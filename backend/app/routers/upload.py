"""
/api/upload — Document upload endpoint.
"""

import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request, UploadFile, File

from app.config import (
    UPLOAD_DIR,
    MAX_UPLOAD_SIZE_BYTES,
    MAX_UPLOAD_SIZE_MB,
    sanitize_filename,
)
from app.models.schemas import UploadResponse
from app.services.ingestion import SUPPORTED_EXTENSIONS

router = APIRouter(tags=["Documents"])


@router.post("/api/upload", response_model=UploadResponse)
async def upload_document(request: Request, file: UploadFile = File(...)):
    """
    Upload a document (PDF, TXT, or MD) to be ingested into the knowledge base.
    
    Security controls:
    - Whitelist validation of extensions (.txt, .pdf, .md)
    - Strict filename sanitization (prevents path traversal ../, null bytes)
    - File size limit enforcement (rejects files > MAX_UPLOAD_SIZE_MB)
    """
    raw_filename = file.filename or "unknown"
    ext = os.path.splitext(raw_filename)[1].lower()

    # 1. Extension check
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type: '{ext}'. "
                f"Supported types: {', '.join(SUPPORTED_EXTENSIONS)}"
            ),
        )

    # 2. Sanitize filename to prevent directory traversal
    filename = sanitize_filename(raw_filename)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    upload_root = Path(UPLOAD_DIR).resolve()
    target_path = (upload_root / filename).resolve()
    
    # Verify canonical path stays strictly inside upload directory
    if not str(target_path).startswith(str(upload_root)):
        raise HTTPException(
            status_code=400,
            detail="Security violation: Invalid file path detected.",
        )

    filepath = str(target_path)

    # 3. Stream file to disk while validating size to prevent memory exhaustion
    total_size = 0
    chunk_size = 1024 * 1024  # 1MB chunks

    try:
        with open(filepath, "wb") as buffer:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > MAX_UPLOAD_SIZE_BYTES:
                    buffer.close()
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    raise HTTPException(
                        status_code=413,
                        detail=(
                            f"File size exceeds the enterprise limit of "
                            f"{MAX_UPLOAD_SIZE_MB}MB."
                        ),
                    )
                buffer.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(filepath):
            os.remove(filepath)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to securely save uploaded file: {str(e)}",
        )

    # Ingest the file
    ingestion = request.app.state.ingestion

    try:
        chunks_created = ingestion.ingest_file(filepath, filename)
        return UploadResponse(
            filename=filename,
            chunks_created=chunks_created,
            status="success",
        )
    except Exception as e:
        # Clean up the saved file on failure
        if os.path.exists(filepath):
            os.remove(filepath)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to ingest document: {str(e)}",
        )
