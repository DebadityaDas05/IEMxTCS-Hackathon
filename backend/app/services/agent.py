"""
LangGraph Agent — StateGraph-based RAG workflow.
Phase 5 Bonus implementation.

Graph Topology:
  START
    │
    ▼
  [retrieve] ─────────────▶ Embeds query, retrieves top-k chunks from ChromaDB
    │
    ▼
  [grade_relevance] ──────▶ Evaluates similarity scores & filters candidate chunks
    │
    ├──▶ (Relevant chunks found) ──▶ [generate] ──▶ [cite_and_format] ──▶ END
    │
    └──▶ (No relevant chunks)    ──▶ [no_answer] ───────────────────────▶ END
"""

import os
from typing import TypedDict, Optional, List
from langgraph.graph import StateGraph, START, END

from app.config import TOP_K, RELEVANCE_THRESHOLD
from app.services.vectorstore import VectorStore
from app.services.llm import LLMService


class RAGAgentState(TypedDict):
    """Internal state for the LangGraph RAG Agent."""
    question: str
    retrieved_chunks: List[dict]
    relevant_chunks: List[dict]
    answer: str
    sources: List[dict]
    is_grounded: bool
    relevance_score: float
    steps: List[str]


class LangGraphRAGAgent:
    """
    Agentic RAG orchestrator built on LangGraph StateGraph.
    Provides intelligent relevance gating, step-by-step trace auditing,
    and hallucination defense.
    """

    def __init__(self, vectorstore: VectorStore, llm: LLMService):
        self.vectorstore = vectorstore
        self.llm = llm
        self.top_k = TOP_K
        self.relevance_threshold = RELEVANCE_THRESHOLD
        self.graph = self._build_graph()

    def _build_graph(self):
        """Constructs and compiles the LangGraph StateGraph."""
        builder = StateGraph(RAGAgentState)

        # Register nodes
        builder.add_node("retrieve", self._retrieve_node)
        builder.add_node("grade_relevance", self._grade_relevance_node)
        builder.add_node("generate", self._generate_node)
        builder.add_node("cite_and_format", self._cite_and_format_node)
        builder.add_node("no_answer", self._no_answer_node)

        # Wire edges
        builder.add_edge(START, "retrieve")
        builder.add_edge("retrieve", "grade_relevance")

        # Conditional branch after grading relevance
        builder.add_conditional_edges(
            "grade_relevance",
            self._relevance_gate,
            {
                "generate": "generate",
                "no_answer": "no_answer",
            },
        )

        builder.add_edge("generate", "cite_and_format")
        builder.add_edge("cite_and_format", END)
        builder.add_edge("no_answer", END)

        return builder.compile()

    # --------------------------------------------------------------------------
    # Graph Nodes
    # --------------------------------------------------------------------------

    def _retrieve_node(self, state: RAGAgentState) -> dict:
        """Node 1: Retrieve candidate chunks from ChromaDB."""
        question = state["question"]
        current_steps = list(state.get("steps", [])) + ["retrieve"]

        raw_chunks = []
        results = self.vectorstore.search(question, top_k=self.top_k)

        if results and results.get("documents") and results["documents"][0]:
            for doc, meta, distance in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                similarity = 1.0 - distance
                raw_chunks.append({
                    "text": doc,
                    "metadata": meta,
                    "score": round(similarity, 3),
                })

        return {
            "retrieved_chunks": raw_chunks,
            "steps": current_steps,
        }

    def _grade_relevance_node(self, state: RAGAgentState) -> dict:
        """
        Node 2: Grade relevance of candidate chunks.
        Applies similarity thresholding to filter noise and hallucination triggers.
        """
        retrieved = state.get("retrieved_chunks", [])
        current_steps = list(state.get("steps", [])) + ["grade_relevance"]

        relevant = []
        max_score = 0.0

        for chunk in retrieved:
            score = chunk.get("score", 0.0)
            if score > max_score:
                max_score = score
            if score >= self.relevance_threshold:
                relevant.append(chunk)

        return {
            "relevant_chunks": relevant,
            "relevance_score": round(max_score, 3),
            "steps": current_steps,
        }

    def _relevance_gate(self, state: RAGAgentState) -> str:
        """Conditional router: checks if sufficient relevant evidence was found."""
        relevant = state.get("relevant_chunks", [])
        if relevant and len(relevant) > 0:
            return "generate"
        return "no_answer"

    def _generate_node(self, state: RAGAgentState) -> dict:
        """Node 3: Generate grounded answer via Ollama LLM."""
        question = state["question"]
        relevant_chunks = state.get("relevant_chunks", [])
        current_steps = list(state.get("steps", [])) + ["generate"]

        raw_answer = self.llm.generate_answer(question, relevant_chunks)

        return {
            "answer": raw_answer,
            "steps": current_steps,
        }

    def _cite_and_format_node(self, state: RAGAgentState) -> dict:
        """Node 4: Extract and format source citations with deduplication."""
        relevant_chunks = state.get("relevant_chunks", [])
        current_steps = list(state.get("steps", [])) + ["cite_and_format"]

        seen_docs = set()
        sources = []

        for chunk in relevant_chunks:
            meta = chunk.get("metadata", {})
            doc_name = meta.get("source", "Unknown")

            if doc_name not in seen_docs:
                seen_docs.add(doc_name)
                sources.append({
                    "document": doc_name,
                    "section": meta.get("section", None),
                    "snippet": chunk.get("text", "")[:350],
                    "score": round(chunk.get("score", 0.0), 3),
                })

        return {
            "sources": sources,
            "is_grounded": True,
            "steps": current_steps,
        }

    def _no_answer_node(self, state: RAGAgentState) -> dict:
        """Fallback Node: Executed when no evidence meets relevance threshold."""
        current_steps = list(state.get("steps", [])) + ["no_answer_fallback"]
        return {
            "answer": "I couldn't find this in the available documents.",
            "sources": [],
            "is_grounded": False,
            "steps": current_steps,
        }

    # --------------------------------------------------------------------------
    # Public Execution Interface
    # --------------------------------------------------------------------------

    def run(self, question: str) -> dict:
        """
        Executes the LangGraph agent workflow for the given question.
        
        Returns:
            dict containing answer, sources, is_grounded, workflow_steps, and relevance_score.
        """
        initial_state: RAGAgentState = {
            "question": question,
            "retrieved_chunks": [],
            "relevant_chunks": [],
            "answer": "",
            "sources": [],
            "is_grounded": False,
            "relevance_score": 0.0,
            "steps": [],
        }

        final_state = self.graph.invoke(initial_state)

        return {
            "answer": final_state.get("answer", ""),
            "sources": final_state.get("sources", []),
            "is_grounded": final_state.get("is_grounded", False),
            "workflow_steps": final_state.get("steps", []),
            "relevance_score": final_state.get("relevance_score", 0.0),
        }
