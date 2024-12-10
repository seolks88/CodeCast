# memory/memory_orchestrator.py
from typing import List, Dict, Any
from memory.rerank_service import RerankService


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
        query_emb = self.embed.get_embedding(query, is_code=False)
        search_results = self.vdb.search(query_emb, top_k=15, namespace="topics")

        # 각 결과에서 text 정보(예: raw_topic_text) 추출
        documents = []
        for res in search_results:
            meta = res["metadata"]
            topic_text = meta.get("raw_topic_text", "")
            documents.append(topic_text)

        # documents가 비어있는 경우 처리 추가
        if not documents:
            return []

        ranked_docs = self.reranker.rerank(query, documents, top_n=5)

        # ranked_docs는 (문서, 점수) 튜플 리스트 형태로 반환되므로,
        # 이를 다시 원하는 형식으로 재구성하여 반환 가능
        # 예: 문서 내용 -> metadata 매핑 필요할 경우 추가 처리
        # 여기서는 단순히 rerank 결과를 반환
        return ranked_docs
