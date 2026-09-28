"""
RAG Retriever — orchestrates vector search, relevance filtering, and answer generation.
"""

from app.services.vectorstore import VectorStore
from app.services.llm import LLMService
from app.config import TOP_K, RELEVANCE_THRESHOLD
from app.models.schemas import AnswerResponse, Source


class RAGRetriever:
    """
    The core RAG pipeline:
    1. Embed the user query
    2. Search ChromaDB for similar chunks
    3. Filter by relevance threshold
    4. Generate a grounded answer with citations
    """

    def __init__(self, vectorstore: VectorStore, llm: LLMService):
        self.vectorstore = vectorstore
        self.llm = llm

    def answer_question(self, question: str) -> AnswerResponse:
        """
        Process a user question through the full RAG pipeline.
        
        Returns an AnswerResponse with the answer, source citations,
        and a flag indicating whether the answer is grounded in documents.
        """
        # Guard: empty question
        if not question or not question.strip():
            return AnswerResponse(
                answer="Please type a question to get started.",
                sources=[],
                is_grounded=False,
            )

        # Guard: no documents in the store
        if self.vectorstore.get_total_count() == 0:
            return AnswerResponse(
                answer="No documents have been uploaded yet. Please upload some documents first.",
                sources=[],
                is_grounded=False,
            )

        # Step 1: Vector similarity search
        results = self.vectorstore.search(question, top_k=TOP_K)

        # Guard: no results returned
        if (
            not results
            or not results.get("documents")
            or not results["documents"][0]
        ):
            return AnswerResponse(
                answer="I couldn't find this in the available documents.",
                sources=[],
                is_grounded=False,
            )

        # Step 2: Filter by relevance threshold
        context_chunks: list[dict] = []
        sources: list[Source] = []

        for doc, meta, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            # ChromaDB cosine distance: 0 = identical, 2 = opposite
            # Convert to similarity: 1 - (distance / 2) maps [0,2] → [1,0]
            # But in practice, chromadb returns 1-cosine_similarity for cosine space
            # So similarity = 1 - distance
            similarity = 1 - distance

            if similarity >= RELEVANCE_THRESHOLD:
                context_chunks.append(
                    {
                        "text": doc,
                        "metadata": meta,
                        "score": similarity,
                    }
                )
                sources.append(
                    Source(
                        document=meta.get("source", "Unknown"),
                        section=meta.get("section"),
                        snippet=doc[:300] + "..." if len(doc) > 300 else doc,
                        score=round(similarity, 3),
                    )
                )

        # Guard: no chunks passed the relevance threshold
        if not context_chunks:
            return AnswerResponse(
                answer="I couldn't find this in the available documents.",
                sources=[],
                is_grounded=False,
            )

        # Step 3: Generate answer from the LLM
        answer = self.llm.generate_answer(question, context_chunks)

        # Sort sources by relevance score (highest first)
        sources.sort(key=lambda s: s.score, reverse=True)

        return AnswerResponse(
            answer=answer,
            sources=sources,
            is_grounded=True,
        )
