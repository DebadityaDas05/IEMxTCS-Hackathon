"""
VectorStore service — ChromaDB wrapper with sentence-transformer embeddings.
"""

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from app.config import CHROMA_PERSIST_DIR, CHROMA_COLLECTION_NAME, EMBEDDING_MODEL


class VectorStore:
    """Manages the ChromaDB vector store for document embeddings."""

    def __init__(self):
        self.embedding_fn = SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL
        )
        self.client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        self.collection = self.client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME,
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )

    def add_documents(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict],
    ) -> None:
        """Add document chunks to the vector store."""
        # ChromaDB has a batch limit, so we chunk the inserts
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            self.collection.add(
                ids=ids[i : i + batch_size],
                documents=documents[i : i + batch_size],
                metadatas=metadatas[i : i + batch_size],
            )

    def search(self, query: str, top_k: int = 5) -> dict:
        """Search for the most similar chunks to a query."""
        results = self.collection.query(
            query_texts=[query],
            n_results=min(top_k, self.collection.count() or 1),
            include=["documents", "metadatas", "distances"],
        )
        return results

    def get_document_stats(self) -> dict[str, int]:
        """Get chunk counts grouped by source document."""
        all_data = self.collection.get(include=["metadatas"])
        stats: dict[str, int] = {}
        for meta in all_data.get("metadatas", []):
            source = meta.get("source", "unknown")
            stats[source] = stats.get(source, 0) + 1
        return stats

    def delete_by_source(self, source_name: str) -> int:
        """Delete all chunks belonging to a specific source document."""
        all_data = self.collection.get(
            where={"source": source_name},
            include=["metadatas"],
        )
        if all_data["ids"]:
            self.collection.delete(ids=all_data["ids"])
            return len(all_data["ids"])
        return 0

    def get_total_count(self) -> int:
        """Get the total number of chunks in the store."""
        return self.collection.count()

    def reset(self) -> None:
        """Delete and recreate the collection (for development/testing)."""
        self.client.delete_collection(CHROMA_COLLECTION_NAME)
        self.collection = self.client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME,
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )
