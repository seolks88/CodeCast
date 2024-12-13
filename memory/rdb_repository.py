# memory/rdb_repository.py
import sqlite3
from typing import List, Dict, Any
from datetime import datetime, timedelta
import json
from rank_bm25 import BM25Okapi
import numpy as np


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

    def search_topics_by_bm25(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        # 1. 최근 토픽들 가져오기
        recent_topics = self.get_recent_topics(days=7)  # 7일치 데이터

        if not recent_topics:
            return []

        # 2. 토픽 텍스트 토큰화
        tokenized_corpus = [doc["raw_topic_text"].lower().split() for doc in recent_topics]
        tokenized_query = query.lower().split()

        # 3. BM25 인스턴스 생성 및 점수 계산
        bm25 = BM25Okapi(tokenized_corpus)
        doc_scores = bm25.get_scores(tokenized_query)

        # 4. 상위 결과 반환
        top_indices = np.argsort(doc_scores)[-limit:][::-1]

        results = []
        for idx in top_indices:
            if doc_scores[idx] > 0:  # 관련성 있는 결과만
                results.append(
                    {
                        "id": recent_topics[idx]["id"],
                        "raw_topic_text": recent_topics[idx]["raw_topic_text"],
                        "date": recent_topics[idx]["date"],
                        "score": float(doc_scores[idx]),  # numpy float을 파이썬 float으로 변환
                    }
                )

        return results
