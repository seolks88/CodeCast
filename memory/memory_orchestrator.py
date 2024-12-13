# memory/memory_orchestrator.py
from typing import List, Dict, Any
from memory.rerank_service import RerankService
import os


class MemoryOrchestrator:
    def __init__(self, rdb_repository, embedding_service, vector_db_client):
        """
        rdb_repository: RDB 관련 CRUD 담당 (RDBRepository 인스턴스)
        embedding_service: EmbeddingService 인스턴스
        vector_db_client: VectorDBClient 인스턴스
        """
        self.rdb = rdb_repository  # RDB 저장소
        self.embed = embedding_service  # 임베딩 서비스
        self.vdb = vector_db_client  # 벡터 DB 클라이언트
        self.reranker = RerankService()  # RerankService 인스턴스 생성

    def add_topic(self, date: str, raw_topic_text: str, context_text: str = "") -> int:
        """
        토픽을 추가하는 메서드

        Args:
            date: 날짜
            raw_topic_text: 원본 토픽 텍스트
            context_text: 컨텍스트 텍스트 (선택사항)

        Returns:
            int: 생성된 토픽 ID
        """
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
        """
        에이전트 리포트를 추가하는 메서드

        Args:
            date: 날짜
            agent_type: 에이전트 유형
            topic_id: 토픽 ID
            report_content: 리포트 내용
            summary: 요약
            code_refs: 코드 참조 목록
            raw_topic_text: 원본 토픽 텍스트

        Returns:
            int: 생성된 리포트 ID
        """
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
        """
        최근 토픽들을 가져오는 메서드

        Args:
            days: 조회할 일수 (기본값: 3일)

        Returns:
            List[Dict[str, Any]]: 최근 토픽 목록
        """
        return self.rdb.get_recent_topics(days)

    def find_similar_topics(self, query: str, top_k: int = 5) -> List[Dict]:
        # 1. BM25 검색 (RDB)
        keyword_results = self.rdb.search_topics_by_bm25(query, limit=top_k)
        combined_results = []

        # VOYAGE_API_KEY가 있는 경우에만 벡터 검색 수행
        if os.getenv("VOYAGE_API_KEY"):
            # 벡터 검색 (VectorDB)
            query_emb = self.embed.get_embedding(query, is_code=False)
            vector_results = self.vdb.search(query_emb, top_k=3, namespace="topics", days=7)

            # 결과 병합 (중복 제거)
            seen_ids = set()

            # BM25 결과 추가
            for result in keyword_results:
                doc_id = result["id"]
                if doc_id not in seen_ids:
                    seen_ids.add(doc_id)
                    combined_results.append(
                        {
                            "document": result["raw_topic_text"],
                            "score": 1.0,  # BM25 결과는 높은 점수
                            "metadata": result,
                        }
                    )

            # 벡터 검색 결과 추가
            for result in vector_results:
                doc_id = result["id"].split("_")[1]
                if doc_id not in seen_ids:
                    seen_ids.add(doc_id)
                    combined_results.append(
                        {
                            "document": result["metadata"]["raw_topic_text"],
                            "score": result["score"],
                            "metadata": result["metadata"],
                        }
                    )
        else:
            # VOYAGE_API_KEY가 없는 경우 BM25 결과만 사용
            combined_results = [
                {"document": result["raw_topic_text"], "score": 1.0, "metadata": result} for result in keyword_results
            ]

        # Reranker가 있으면 사용, 없으면 기존 점수로 정렬
        if hasattr(self, "reranker") and self.reranker and os.getenv("COHERE_API_KEY"):
            documents = [r["document"] for r in combined_results]
            reranked = self.reranker.rerank(query, documents, top_n=min(5, len(documents)))
            return reranked
        else:
            # Reranker 없을 때는 기존 점수로 정렬
            sorted_results = sorted(combined_results, key=lambda x: x["score"], reverse=True)
            return sorted_results[:top_k]
