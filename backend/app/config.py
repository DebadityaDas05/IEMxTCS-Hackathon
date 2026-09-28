import os
import re
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the backend directory
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Security & Environment
ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development").lower()
SECRET_KEY: str = os.getenv("SECRET_KEY", "iem-tcs-enterprise-knowledge-assistant-default-key-change-in-prod")
API_KEY_ENABLED: bool = os.getenv("API_KEY_ENABLED", "false").lower() in ("true", "1", "yes")
API_KEY: str = os.getenv("API_KEY", "")

# CORS Configuration
_raw_cors = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
)
CORS_ORIGINS: list[str] = [origin.strip() for origin in _raw_cors.split(",") if origin.strip()]

# Limits & Validation
MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "25"))
MAX_UPLOAD_SIZE_BYTES: int = MAX_UPLOAD_SIZE_MB * 1024 * 1024
MAX_QUESTION_LENGTH: int = int(os.getenv("MAX_QUESTION_LENGTH", "1000"))

# Ollama
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1")

# ChromaDB
CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
CHROMA_COLLECTION_NAME: str = os.getenv("CHROMA_COLLECTION_NAME", "knowledge_base")

# Embeddings
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# Chunking
CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "50"))

# Retrieval
TOP_K: int = int(os.getenv("TOP_K", "5"))
RELEVANCE_THRESHOLD: float = float(os.getenv("RELEVANCE_THRESHOLD", "0.3"))

# Upload
UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./data/uploads")
SAMPLE_DOCS_DIR: str = os.getenv("SAMPLE_DOCS_DIR", "./data/sample_docs")

# Ensure directories exist
os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(SAMPLE_DOCS_DIR, exist_ok=True)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize an uploaded filename to prevent directory traversal and injection.
    Strips directory separators and keeps only safe alphanumeric, dash, dot, and underscore.
    """
    # Take only the base name (strip directory paths like ../ or C:\)
    base = os.path.basename(filename.strip().replace("\\", "/"))
    # Replace any character that is not alphanumeric, underscore, dot, or hyphen
    sanitized = re.sub(r"[^a-zA-Z0-9_.-]", "_", base)
    # Avoid empty names or names starting with dots (hidden files)
    if not sanitized or sanitized.startswith("."):
        sanitized = f"upload_{sanitized.lstrip('.') or 'file'}"
    return sanitized

