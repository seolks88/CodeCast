# memory/memory_orchestrator.py
from typing import List, Dict, Any
from datetime import datetime
import json


class MemoryOrchestrator:
    def __init__(self, rdb_repository, embedding_service, vector_db_client):
        """
        rdb_repository: RDB 관련 CRUD 담당 (RDBRepository 인스턴스)
        embedding_service: EmbeddingService 인스턴스
        vector_db_client: VectorDBClient 인스턴스
        """
        self.rdb = rdb_repository
        self.embed = embedding_service
        self.vdb = vector_db_client

    def add_topic(self, date: str, raw_topic_text: str, context_text: str = "") -> int:
        topic_id = self.rdb.add_topic(date, raw_topic_text)
        combined_text = f"{raw_topic_text}\n\n[Context]: {context_text}" if context_text else raw_topic_text
        topic_emb = self.embed.get_embedding(combined_text, is_code=False)
        self.vdb.upsert_vector(
            f"topic_{topic_id}",
            topic_emb,
            {"raw_topic_text": raw_topic_text, "context_text": context_text, "date": date},
            namespace="topics",
        )
        return topic_id

    def add_agent_report(
        self,
        date: str,
        agent_type: str,
        topic_id: int,
        report_content: str,
        summary: str,
        code_refs: List[str],
        raw_topic_text: str,
    ) -> int:
        report_id = self.rdb.add_agent_report(
            date, agent_type, topic_id, report_content, summary, code_refs, raw_topic_text
        )

        report_emb = self.embed.get_embedding(report_content, is_code=False)
        self.vdb.upsert_vector(
            f"report_{report_id}",
            report_emb,
            {
                "agent_type": agent_type,
                "topic_id": topic_id,
                "date": date,
                "summary": summary,
                "raw_topic_text": raw_topic_text,
                "report_id": report_id,
            },
            namespace="reports",
        )
        return report_id

    def get_recent_topics(self, days: int = 3) -> List[Dict[str, Any]]:
        return self.rdb.get_recent_topics(days)

    def find_similar_topics(self, query: str, top_k=5):
        query_emb = self.embed.get_embedding(query, is_code=False)
        return self.vdb.search(query_emb, top_k, namespace="topics")

    def get_habit_occurrences(self, habit_name: str) -> int:
        query_text = f"Habit: {habit_name}, occurrences:"
        query_emb = self.embed.get_embedding(query_text, is_code=False)
        results = self.vdb.search(query_emb, top_k=5, namespace="habits")

        for r in results:
            md = r["metadata"]
            if md.get("habit_name") == habit_name:
                return md.get("occurrences", 0)
        return 0

    def record_habit_occurrence(self, habit_name: str, improvement: bool = False):
        current_occ = self.get_habit_occurrences(habit_name)
        if improvement:
            current_occ = max(0, current_occ - 1)
        else:
            current_occ += 1

        habit_id = f"habit_{habit_name}"
        habit_text = f"Habit: {habit_name}, occurrences: {current_occ}"
        habit_emb = self.embed.get_embedding(habit_text, is_code=False)
        metadata = {
            "habit_name": habit_name,
            "occurrences": current_occ,
            "last_mentioned_date": datetime.now().isoformat(),
        }
        self.vdb.upsert_vector(habit_id, habit_emb, metadata, namespace="habits")

    def find_similar_habits(self, query: str, top_k=5):
        query_emb = self.embed.get_embedding(query, is_code=False)
        return self.vdb.search(query_emb, top_k, namespace="habits")
