# memory/vector_db_client.py

import chromadb


class VectorDBClient:
    def __init__(self, persist_directory=".chroma_db"):
        # PersistentClient 사용
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collections = {}
        # cosine 거리 사용을 위해 metadata에 hnsw:space 설정 (필요하다면)
        for namespace in ["topics", "reports", "habits", "code_snippets"]:
            self.collections[namespace] = self.client.get_or_create_collection(
                name=namespace,
                metadata={"hnsw:space": "cosine"},
            )

    def upsert_vector(self, doc_id: str, embedding: list, metadata: dict, namespace: str):
        """
        doc_id를 해당 문서의 고유 ID로 사용.
        embeddings, documents, metadatas 등을 upsert.
        여기서는 documents를 doc_id로 대체 가능하지만, 필요하다면 documents 필드에 실제 문서 내용도 저장 가능.
        """
        # documents를 doc_id 자체나 빈 문자열로 둘 수도 있음.
        # 여기서는 doc_id를 documents에도 넣어 문서 식별에 활용 가능.
        # 실제 문서 내용이 있다면 documents로 전달.
        collection = self.collections[namespace]
        collection.upsert(
            documents=[doc_id],  # 실제 문서 내용 대신 doc_id로 대체 가능 (원하는 경우)
            embeddings=[embedding],
            metadatas=[metadata],
            ids=[doc_id],
        )

    def search(self, query_embedding: list, top_k: int, namespace: str):
        """
        query_embedding으로 유사도 검색 수행.
        반환 형식:
        [
          {
            "id": str,
            "metadata": dict,
            "score": float
          },
          ...
        ]
        """
        collection = self.collections[namespace]
        results = collection.query(query_embeddings=[query_embedding], n_results=top_k)
        output = []
        for i, doc_id in enumerate(results["ids"][0]):
            distance = results["distances"][0][i]
            similarity = 1 - distance
            output.append(
                {
                    "id": doc_id,
                    "metadata": results["metadatas"][0][i],
                    "score": similarity,
                }
            )
        return output

    def get_by_doc_id(self, doc_id: str, namespace: str, include=["documents", "metadatas", "ids"]):
        """
        doc_id로 특정 문서를 조회.
        collection.get()을 사용하면 해당 id와 일치하는 문서를 바로 가져올 수 있다.
        include 파라미터로 반환할 필드 지정 가능: "documents", "metadatas", "embeddings", "distances"

        예: include=["documents","metadatas","embeddings","ids"]
        """
        collection = self.collections[namespace]
        results = collection.get(ids=[doc_id], include=include)

        # results 형식 예:
        # {
        #   "ids": [["id1"]],
        #   "documents": [["..."]],
        #   "metadatas": [[{...}]],
        #   "embeddings": [[[...]]],
        # }
        # 각 필드는 2차원 리스트 형태.
        if len(results["ids"]) > 0 and len(results["ids"][0]) > 0:
            idx = 0
            ret = {"id": results["ids"][0][idx]}
            if "documents" in include and "documents" in results:
                ret["document"] = (
                    results["documents"][0][idx] if results["documents"] and results["documents"][0] else None
                )
            if "metadatas" in include and "metadatas" in results:
                ret["metadata"] = (
                    results["metadatas"][0][idx] if results["metadatas"] and results["metadatas"][0] else None
                )
            if "embeddings" in include and "embeddings" in results:
                ret["embedding"] = (
                    results["embeddings"][0][idx] if results["embeddings"] and results["embeddings"][0] else None
                )
            # distances는 get에서 지원하지 않음(query에서만)
            return ret
        return None
