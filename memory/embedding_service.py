# memory/embedding_service.py
import os
import voyageai


class EmbeddingService:
    def __init__(self):
        self.vo = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))

    def get_embedding(self, text: str, is_code: bool = False) -> list:
        model = "voyage-code-3" if is_code else "voyage-multilingual-2"
        result = self.vo.embed([text], model=model)
        return result.embeddings[0]
