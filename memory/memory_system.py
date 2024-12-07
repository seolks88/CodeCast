import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
from memory.embedding_service import EmbeddingService
from memory.vector_db_client import VectorDBClient


class MemorySystem:
    def __init__(self, db_path: str, vector_db_path: str = ".chroma_db"):
        self.db_path = db_path
        self.vector_client = VectorDBClient(persist_directory=vector_db_path)
        self.embedding_service = EmbeddingService()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def add_topic(self, date: str, raw_topic_text: str) -> int:
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("INSERT INTO topics (date, raw_topic_text) VALUES (?, ?)", (date, raw_topic_text))
        topic_id = c.lastrowid
        conn.commit()
        conn.close()

        topic_emb = self.embedding_service.get_embedding(raw_topic_text, is_code=False)
        self.vector_client.upsert_vector(
            f"topic_{topic_id}", topic_emb, {"raw_topic_text": raw_topic_text, "date": date}, namespace="topics"
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
            },
            namespace="reports",
        )
        return report_id

    def update_concept_difficulty(self, concept: str, difficulty: str):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute(
            """
        INSERT INTO user_learning_progress (concept, difficulty_level, last_mentioned_date)
        VALUES (?, ?, ?)
        ON CONFLICT(concept) DO UPDATE SET difficulty_level=excluded.difficulty_level, last_mentioned_date=excluded.last_mentioned_date
        """,
            (concept, difficulty, datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()

        concept_text = f"{concept} - difficulty:{difficulty}"
        concept_emb = self.embedding_service.get_embedding(concept_text, is_code=False)
        self.vector_client.upsert_vector(
            f"concept_{concept}", concept_emb, {"concept": concept, "difficulty": difficulty}, namespace="concepts"
        )

    def get_concept_difficulty(self, concept: str) -> str:
        # 개념 난이도 조회
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT difficulty_level FROM user_learning_progress WHERE concept=?", (concept,))
        row = c.fetchone()
        conn.close()
        return row[0] if row else None

    def record_habit_occurrence(self, habit_name: str, improvement: bool = False):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT occurrences FROM user_habits WHERE habit_name = ?", (habit_name,))
        row = c.fetchone()
        now = datetime.now().isoformat()
        if row:
            occ = row[0] + (-1 if improvement else 1)
            if occ < 0:
                occ = 0
            c.execute(
                "UPDATE user_habits SET occurrences=?, last_mentioned_date=? WHERE habit_name=?", (occ, now, habit_name)
            )
        else:
            occ = 1
            c.execute(
                "INSERT INTO user_habits (habit_name, occurrences, last_mentioned_date) VALUES (?, ?, ?)",
                (habit_name, occ, now),
            )
        conn.commit()
        conn.close()

        habit_text = f"Habit: {habit_name}, occurrences: {occ}"
        habit_emb = self.embedding_service.get_embedding(habit_text, is_code=False)
        self.vector_client.upsert_vector(
            f"habit_{habit_name}", habit_emb, {"habit_name": habit_name, "occurrences": occ}, namespace="habits"
        )

    def get_habit_occurrences(self, habit_name: str) -> int:
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT occurrences FROM user_habits WHERE habit_name=?", (habit_name,))
        row = c.fetchone()
        conn.close()
        return row[0] if row else 0

    def index_code_snippet(self, snippet_id: str, code_snippet: str, file_path: str):
        emb = self.embedding_service.get_embedding(code_snippet, is_code=True)
        self.vector_client.upsert_vector(snippet_id, emb, {"file_path": file_path}, namespace="code_snippets")

    def get_recent_topics(self, days: int = 3) -> List[Dict[str, Any]]:
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT id, raw_topic_text, date FROM topics WHERE date >= ?", (cutoff_date,))
        rows = c.fetchall()
        conn.close()
        return [{"id": r[0], "raw_topic_text": r[1], "date": r[2]} for r in rows]

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

    def find_similar_code_snippets(self, query: str, top_k=5):
        query_emb = self.embedding_service.get_embedding(query, is_code=True)
        return self.vector_client.search(query_emb, top_k, namespace="code_snippets")
