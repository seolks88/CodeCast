# memory/memory_system.py

import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
import sqlite3
from memory.embedding_service import EmbeddingService
from memory.vector_db_client import VectorDBClient


class MemorySystem:
    """
    Hybrid Storage Policy:
    - Topics, reports: stored in RDB + VectorDB (for semantic search on topics/reports)
    - Concepts and habits: stored ONLY in VectorDB (no RDB usage)
    - File changes, analysis results: still in RDB

    Below logic reflects that concepts and habits are no longer in RDB, and we rely on VectorDB and metadata.
    """

    def __init__(self, db_path: str, vector_db_path: str = ".chroma_db"):
        self.db_path = db_path
        self.vector_client = VectorDBClient(persist_directory=vector_db_path)
        self.embedding_service = EmbeddingService()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def add_topic(self, date: str, raw_topic_text: str, context_text: str = "") -> int:
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("INSERT INTO topics (date, raw_topic_text) VALUES (?, ?)", (date, raw_topic_text))
        topic_id = c.lastrowid
        conn.commit()
        conn.close()

        # 토픽 임베딩 생성 시 context 함께 포함
        if context_text:
            combined_text = f"{raw_topic_text}\n\n[Context]: {context_text}"
        else:
            combined_text = raw_topic_text

        topic_emb = self.embedding_service.get_embedding(combined_text, is_code=False)

        self.vector_client.upsert_vector(
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
    ):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO agent_reports (date, agent_type, topic_id, report_content, summary, code_references, raw_topic_text)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (date, agent_type, topic_id, report_content, summary, json.dumps(code_refs), raw_topic_text),
        )
        report_id = c.lastrowid
        conn.commit()
        conn.close()

        report_emb = self.embedding_service.get_embedding(report_content, is_code=False)
        self.vector_client.upsert_vector(
            f"report_{report_id}",
            report_emb,
            {
                "agent_type": agent_type,
                "topic_id": topic_id,
                "date": date,
                "summary": summary,
                "raw_topic_text": raw_topic_text,
                "report_id": report_id,  # report_id 추가
            },
            namespace="reports",
        )
        return report_id

    def get_report_by_id(self, report_id: int) -> Dict[str, Any]:
        conn = self._get_conn()
        c = conn.cursor()
        c.execute(
            "SELECT date, agent_type, topic_id, report_content, summary, code_references, raw_topic_text FROM agent_reports WHERE id=?",
            (report_id,),
        )
        row = c.fetchone()
        conn.close()
        if row:
            return {
                "date": row[0],
                "agent_type": row[1],
                "topic_id": row[2],
                "report_content": row[3],
                "summary": row[4],
                "code_references": json.loads(row[5]) if row[5] else [],
                "raw_topic_text": row[6],
            }
        return {}

    def get_concept_difficulty(self, concept: str) -> str:
        query_text = f"{concept} - difficulty:"
        query_emb = self.embedding_service.get_embedding(query_text, is_code=False)
        results = self.vector_client.search(query_emb, top_k=5, namespace="concepts")

        for r in results:
            md = r["metadata"]
            if md.get("concept") == concept:
                return md.get("difficulty")
        # 정보가 없으면 기본값 "basic" 반환
        return "basic"

    def get_habit_occurrences(self, habit_name: str) -> int:
        query_text = f"Habit: {habit_name}, occurrences:"
        query_emb = self.embedding_service.get_embedding(query_text, is_code=False)
        results = self.vector_client.search(query_emb, top_k=5, namespace="habits")

        for r in results:
            md = r["metadata"]
            if md.get("habit_name") == habit_name:
                return md.get("occurrences", 0)
        # 정보가 없으면 0으로 초기화
        return 0

    def record_habit_occurrence(self, habit_name: str, improvement: bool = False):
        current_occ = self.get_habit_occurrences(habit_name)
        if improvement:
            current_occ = max(0, current_occ - 1)
        else:
            current_occ += 1

        habit_id = f"habit_{habit_name}"
        habit_text = f"Habit: {habit_name}, occurrences: {current_occ}"
        habit_emb = self.embedding_service.get_embedding(habit_text, is_code=False)
        metadata = {
            "habit_name": habit_name,
            "occurrences": current_occ,
            "last_mentioned_date": datetime.now().isoformat(),
        }
        self.vector_client.upsert_vector(habit_id, habit_emb, metadata, namespace="habits")

    def find_similar_topics(self, query: str, top_k=5):
        query_emb = self.embedding_service.get_embedding(query, is_code=False)
        return self.vector_client.search(query_emb, top_k, namespace="topics")

    def find_similar_reports(self, query: str, top_k=5):
        query_emb = self.embedding_service.get_embedding(query, is_code=False)
        return self.vector_client.search(query_emb, top_k, namespace="reports")

    def find_similar_concepts(self, query: str, top_k=5):
        query_emb = self.embedding_service.get_embedding(query, is_code=False)
        return self.vector_client.search(query_emb, top_k, namespace="concepts")

    def find_similar_habits(self, query: str, top_k=5):
        query_emb = self.embedding_service.get_embedding(query, is_code=False)
        return self.vector_client.search(query_emb, top_k, namespace="habits")

    def get_recent_topics(self, days: int = 3) -> List[Dict[str, Any]]:
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT id, raw_topic_text, date FROM topics WHERE date >= ?", (cutoff_date,))
        rows = c.fetchall()
        conn.close()
        return [{"id": r[0], "raw_topic_text": r[1], "date": r[2]} for r in rows]

    def index_code_snippet(self, snippet_id: str, code_snippet: str, file_path: str):
        emb = self.embedding_service.get_embedding(code_snippet, is_code=True)
        self.vector_client.upsert_vector(snippet_id, emb, {"file_path": file_path}, namespace="code_snippets")

    def update_concept_difficulty(self, concept: str, new_difficulty: str):
        """
        주어진 개념의 난이도를 업데이트하는 메서드.
        기존에 개념 벡터가 없다면 새로 생성, 있으면 업데이트.
        """

        # 기존 개념 메타데이터 조회
        query_text = f"{concept} - difficulty:"
        query_emb = self.embedding_service.get_embedding(query_text, is_code=False)
        results = self.vector_client.search(query_emb, top_k=5, namespace="concepts")

        # 기존 엔트리 있으면 가져오기
        existing_id = None
        existing_metadata = {}
        for r in results:
            md = r["metadata"]
            if md.get("concept") == concept:
                existing_id = r["id"]
                existing_metadata = md
                break

        # 메타데이터 갱신
        if not existing_metadata:
            existing_metadata = {
                "concept": concept,
                "difficulty": new_difficulty,
                "last_mentioned_date": datetime.now().isoformat(),
            }
        else:
            existing_metadata["difficulty"] = new_difficulty
            existing_metadata["last_mentioned_date"] = datetime.now().isoformat()

        # 개념 텍스트를 기반으로 임베딩 재생성 (필수는 아니지만, consistency를 위해 동일한 query_text 사용)
        concept_text = f"Concept: {concept}, difficulty: {new_difficulty}"
        concept_emb = self.embedding_service.get_embedding(concept_text, is_code=False)

        # id 설정
        concept_id = existing_id if existing_id else f"concept_{concept}"

        # 벡터 DB에 업서트
        self.vector_client.upsert_vector(
            doc_id=concept_id, embedding=concept_emb, metadata=existing_metadata, namespace="concepts"
        )
