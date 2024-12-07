# memory/vector_db_client.py
import chromadb


class VectorDBClient:
    def __init__(self, persist_directory=".chroma_db"):
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collections = {}
        for namespace in ["topics", "reports", "concepts", "habits", "code_snippets"]:
            self.collections[namespace] = self.client.get_or_create_collection(name=namespace)

    def upsert_vector(self, doc_id: str, embedding: list, metadata: dict, namespace: str):
        collection = self.collections[namespace]
        collection.upsert(documents=[doc_id], embeddings=[embedding], metadatas=[metadata], ids=[doc_id])

    def search(self, query_embedding: list, top_k: int, namespace: str):
        collection = self.collections[namespace]
        results = collection.query(query_embeddings=[query_embedding], n_results=top_k)
        output = []
        for i, doc_id in enumerate(results["ids"][0]):
            output.append({"id": doc_id, "metadata": results["metadatas"][0][i], "score": results["distances"][0][i]})
        return output
