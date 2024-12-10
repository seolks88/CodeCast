# memory/rerank_service.py
import os
import cohere


class RerankService:
    def __init__(self):
        self.co = cohere.Client(api_key=os.getenv("COHERE_API_KEY"))

    def rerank(self, query: str, documents: list, top_n: int = 5):
        response = self.co.rerank(
            model="rerank-v3.5",
            query=query,
            documents=documents,
            top_n=top_n,
        )

        # 'score' 키를 사용해 일관성 유지
        ranked_docs = [
            {
                "document": documents[d.index],
                "score": d.relevance_score,  # 여기서 score 사용
            }
            for d in response.results
        ]
        return ranked_docs
