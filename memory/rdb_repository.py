# memory/rdb_repository.py
import sqlite3
from typing import List, Dict, Any
from datetime import datetime, timedelta
import json


class RDBRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def add_topic(self, date: str, raw_topic_text: str) -> int:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO topics (date, raw_topic_text) VALUES (?, ?)", (date, raw_topic_text))
        topic_id = c.lastrowid
        conn.commit()
        conn.close()
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
        conn = sqlite3.connect(self.db_path)
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
        return report_id

    def get_recent_topics(self, days: int = 3) -> List[Dict[str, Any]]:
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT id, raw_topic_text, date FROM topics WHERE date >= ?", (cutoff_date,))
        rows = c.fetchall()
        conn.close()
        return [{"id": r[0], "raw_topic_text": r[1], "date": r[2]} for r in rows]
