"""
LLM service — Ollama integration for answer generation.
"""

import ollama  # type: ignore
from app.config import OLLAMA_MODEL


SYSTEM_PROMPT = """You are an intelligent enterprise knowledge assistant for Acme Corporation. Your role is to answer employee questions using ONLY the provided document context.

STRICT RULES:
1. Answer ONLY based on the provided context below. Do NOT use any external or general knowledge.
2. If the context does not contain enough information to answer the question, respond EXACTLY with: "I couldn't find this in the available documents."
3. Always cite the source document name in your answer using the format: (Source: DocumentName)
4. If section information is visible in the context, include it: (Source: DocumentName, Section X.X)
5. Be concise, direct, and helpful in your answers.
6. If the question is very short or ambiguous (e.g., just "leave?" or "policy?"), ask ONE clarifying question before answering.
7. Do not make up, infer, or extrapolate information that is not explicitly stated in the context.
8. If multiple documents are relevant, cite all of them.

CONTEXT FROM COMPANY DOCUMENTS:
---
{context}
---

Remember: You must ONLY use information from the context above. Never fabricate an answer."""


class LLMService:
    """Handles interaction with the Ollama LLM for grounded answer generation."""

    def __init__(self):
        self.model = OLLAMA_MODEL

    def generate_answer(self, question: str, context_chunks: list[dict]) -> str:
        """
        Generate an answer grounded in the provided context chunks.
        
        Args:
            question: The user's question.
            context_chunks: List of dicts with 'text' and 'metadata' keys.
        
        Returns:
            The generated answer string.
        """
        # Format context with source labels
        context_parts = []
        for chunk in context_chunks:
            source = chunk["metadata"].get("source", "Unknown")
            chunk_idx = chunk["metadata"].get("chunk_index", "?")
            context_parts.append(
                f"[Source: {source} | Chunk {chunk_idx}]\n{chunk['text']}"
            )

        context_text = "\n\n---\n\n".join(context_parts)
        system_prompt = SYSTEM_PROMPT.format(context=context_text)

        response = ollama.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
        )

        return response["message"]["content"]

    def check_health(self) -> bool:
        """Check if Ollama is running and the model is available."""
        try:
            models_res = ollama.list()
            # Support both ListResponse.models (objects) and dict-based responses
            items = getattr(models_res, "models", None)
            if items is None and isinstance(models_res, dict):
                items = models_res.get("models", [])
            items = items or []

            model_names = []
            for m in items:
                name = getattr(m, "model", None) or getattr(m, "name", None)
                if not name and isinstance(m, dict):
                    name = m.get("model") or m.get("name")
                if name:
                    model_names.append(str(name))

            # Check if our model (or a variant) is available
            return any(self.model in name for name in model_names)
        except Exception:
            return False
