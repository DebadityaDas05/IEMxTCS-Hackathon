"""
Enterprise Knowledge Assistant — Model Context Protocol (MCP) Server.
Phase 5 Bonus implementation.

Exposes the ChromaDB vector store and LangGraph RAG Agent as standardized
MCP tools and resources, allowing external LLM clients (Claude Desktop,
Antigravity, Cursor, etc.) to query enterprise policies directly.
"""

import sys
import os
import json

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure backend root is on sys.path
backend_root = os.path.dirname(os.path.abspath(__file__))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from mcp.server.mcpserver import MCPServer
from app.services.vectorstore import VectorStore
from app.services.llm import LLMService
from app.services.agent import LangGraphRAGAgent

# Initialize Core Services
vectorstore = VectorStore()
llm = LLMService()
agent = LangGraphRAGAgent(vectorstore, llm)

# Initialize MCP Server
server = MCPServer(
    name="enterprise-knowledge-assistant",
    version="1.0.0",
    description="Enterprise Knowledge Assistant RAG tool suite powered by ChromaDB & LangGraph",
)


# ------------------------------------------------------------------------------
# MCP Tools
# ------------------------------------------------------------------------------

@server.tool(
    name="ask_enterprise_knowledge_base",
    description=(
        "Query the company policy knowledge base using the LangGraph Agentic RAG pipeline. "
        "Returns grounded answers with strict source document citations. "
        "Will explicitly indicate if no relevant policy is found."
    ),
)
def ask_enterprise_knowledge_base(question: str) -> str:
    """
    Ask a question against company policies and guidelines.

    Args:
        question: The user's question about company policies, leave, IT security, travel, etc.

    Returns:
        JSON string containing answer, citations, grounded status, and agent workflow trace.
    """
    if not question or not question.strip():
        return json.dumps({
            "error": "Question cannot be empty.",
            "answer": "Please provide a valid question.",
        })

    result = agent.run(question.strip())
    return json.dumps(result, indent=2)


@server.tool(
    name="list_enterprise_documents",
    description="List all active enterprise policy documents in the knowledge base along with chunk counts.",
)
def list_enterprise_documents() -> str:
    """
    List all indexed enterprise documents.

    Returns:
        JSON formatted list of documents and chunk statistics.
    """
    stats = vectorstore.get_document_stats()
    docs = [
        {"filename": name, "chunk_count": count}
        for name, count in sorted(stats.items())
    ]
    return json.dumps({
        "documents": docs,
        "total_documents": len(docs),
        "total_chunks": vectorstore.get_total_count(),
    }, indent=2)


@server.tool(
    name="search_raw_document_chunks",
    description="Perform semantic similarity search over document chunks and return raw excerpts with scores.",
)
def search_raw_document_chunks(query: str, top_k: int = 5) -> str:
    """
    Direct similarity search on ChromaDB vector store.

    Args:
        query: The semantic search query string.
        top_k: Number of candidate chunks to retrieve (default: 5).

    Returns:
        JSON array of matching chunks, scores, and metadata.
    """
    results = vectorstore.search(query, top_k=top_k)
    chunks = []

    if results and results.get("documents") and results["documents"][0]:
        for doc, meta, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            chunks.append({
                "document": meta.get("source", "Unknown"),
                "section": meta.get("section"),
                "similarity_score": round(1.0 - distance, 3),
                "text": doc,
            })

    return json.dumps({"query": query, "chunks": chunks}, indent=2)


# ------------------------------------------------------------------------------
# MCP Resources
# ------------------------------------------------------------------------------

@server.resource(
    uri="knowledge://documents",
    name="Active Enterprise Documents",
    description="Real-time catalog of all indexed policy documents in the knowledge base.",
    mime_type="application/json",
)
def get_documents_resource() -> str:
    stats = vectorstore.get_document_stats()
    return json.dumps(stats, indent=2)


@server.resource(
    uri="knowledge://health",
    name="Knowledge Base Health Status",
    description="Health status of vector store and Ollama LLM connection.",
    mime_type="application/json",
)
def get_health_resource() -> str:
    return json.dumps({
        "status": "healthy",
        "ollama_connected": llm.check_health(),
        "ollama_model": llm.model,
        "total_chunks": vectorstore.get_total_count(),
    }, indent=2)


# ------------------------------------------------------------------------------
# CLI Entrypoint
# ------------------------------------------------------------------------------

def main():
    """Run the MCP server over stdio or specified transport."""
    transport = "stdio"
    if "--sse" in sys.argv:
        transport = "sse"
    elif "--http" in sys.argv:
        transport = "streamable-http"

    # If running with --test argument, execute a sample query and print results
    if "--test" in sys.argv:
        print("🧪 Testing MCP Server tools directly...")
        print("1. list_enterprise_documents:")
        print(list_enterprise_documents())
        print("\n2. ask_enterprise_knowledge_base:")
        print(ask_enterprise_knowledge_base("What is the probation period?"))
        return

    server.run(transport=transport)


if __name__ == "__main__":
    main()
