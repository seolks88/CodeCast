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
        sorted_docs = sorted(response.results, key=lambda x: x["relevance_score"], reverse=True)
        ranked_docs = [(documents[d["index"]], d["relevance_score"]) for d in sorted_docs]
        return ranked_docs
