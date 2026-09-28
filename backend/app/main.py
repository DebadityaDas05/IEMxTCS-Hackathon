"""
FastAPI application — entry point for the Knowledge Assistant backend.

Initializes all services (VectorStore, LLM, Ingestion, Retriever)
and mounts the API routers.
"""

import os
import sys
from contextlib import asynccontextmanager

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import SAMPLE_DOCS_DIR
from app.models.schemas import HealthResponse
from app.services.vectorstore import VectorStore
from app.services.llm import LLMService
from app.services.ingestion import IngestionService
from app.services.retriever import RAGRetriever
from app.services.agent import LangGraphRAGAgent
from app.routers import ask, upload, documents


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan: initialize services on startup,
    optionally ingest sample documents, and clean up on shutdown.
    """
    print("🚀 Initializing Knowledge Assistant services...")

    # Initialize core services
    vectorstore = VectorStore()
    llm = LLMService()
    ingestion = IngestionService(vectorstore)
    retriever = RAGRetriever(vectorstore, llm)
    agent = LangGraphRAGAgent(vectorstore, llm)

    # Store on app state for router access
    app.state.vectorstore = vectorstore
    app.state.llm = llm
    app.state.ingestion = ingestion
    app.state.retriever = retriever
    app.state.agent = agent

    # Auto-ingest sample documents if the store is empty
    if vectorstore.get_total_count() == 0 and os.path.isdir(SAMPLE_DOCS_DIR):
        print(f"📄 Ingesting sample documents from {SAMPLE_DOCS_DIR}...")
        results = ingestion.ingest_directory(SAMPLE_DOCS_DIR)
        for filename, result in results.items():
            status = result["status"]
            chunks = result["chunks"]
            icon = "✅" if status == "success" else "❌"
            print(f"   {icon} {filename}: {chunks} chunks ({status})")
        print(f"📊 Total chunks in store: {vectorstore.get_total_count()}")
    else:
        print(f"📊 Existing knowledge base: {vectorstore.get_total_count()} chunks")

    # Check Ollama health
    if llm.check_health():
        print(f"🤖 Ollama connected (model: {llm.model})")
    else:
        print(f"⚠️  Ollama not available or model '{llm.model}' not found. "
              f"Make sure Ollama is running and the model is pulled.")

    print("✅ Knowledge Assistant is ready!")

    yield  # Application runs here

    print("🛑 Shutting down Knowledge Assistant...")

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import (
    SAMPLE_DOCS_DIR,
    CORS_ORIGINS,
    ENVIRONMENT,
    API_KEY_ENABLED,
    API_KEY,
)
from app.models.schemas import HealthResponse
from app.services.vectorstore import VectorStore
from app.services.llm import LLMService
from app.services.ingestion import IngestionService
from app.services.retriever import RAGRetriever
from app.routers import ask, upload, documents


# Create the FastAPI application
app = FastAPI(
    title="Intelligent Enterprise Knowledge Assistant",
    description=(
        "A secure, grounded enterprise RAG-based document Q&A system that answers "
        "questions using company documents with source citations."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def standard_security_middleware(request: Request, call_next):
    """
    Standard Enterprise Security Middleware:
    1. Optional API key authentication for protected endpoints.
    2. Enforces industry-standard HTTP security headers.
    """
    # 1. API Key verification (if enabled in environment)
    if API_KEY_ENABLED and request.url.path.startswith("/api/"):
        client_key = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
        if not client_key and "authorization" in request.headers:
            auth_header = request.headers["authorization"]
            if auth_header.lower().startswith("bearer "):
                client_key = auth_header[7:].strip()
        if client_key != API_KEY:
            return JSONResponse(
                status_code=401,
                content={"detail": "Unauthorized: Invalid or missing enterprise API key."},
            )

    # Process request
    response: Response = await call_next(request)

    # 2. Standard Enterprise Security Headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
        "magnetometer=(), microphone=(), payment=(), usb=()"
    )
    if ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response


# CORS middleware — restricted to trusted client origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ask.router)
app.include_router(upload.router)
app.include_router(documents.router)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check the health of the application and its dependencies."""
    vectorstore: VectorStore = app.state.vectorstore
    llm: LLMService = app.state.llm

    stats = vectorstore.get_document_stats()

    return HealthResponse(
        status="healthy",
        ollama_connected=llm.check_health(),
        documents_loaded=len(stats),
        total_chunks=vectorstore.get_total_count(),
    )
