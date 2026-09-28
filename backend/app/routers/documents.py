import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request

from app.config import UPLOAD_DIR, sanitize_filename
from app.models.schemas import DocumentInfo, DocumentListResponse

router = APIRouter(tags=["Documents"])


@router.get("/api/documents", response_model=DocumentListResponse)
async def list_documents(request: Request):
    """List all ingested documents and their chunk counts."""
    vectorstore = request.app.state.vectorstore

    stats = vectorstore.get_document_stats()
    documents = [
        DocumentInfo(filename=name, chunk_count=count)
        for name, count in sorted(stats.items())
    ]
    total_chunks = sum(doc.chunk_count for doc in documents)

    return DocumentListResponse(
        documents=documents,
        total_chunks=total_chunks,
    )


@router.delete("/api/documents/{filename}")
async def delete_document(request: Request, filename: str):
    """
    Delete a document and all its chunks from the knowledge base.
    Also removes the physical file from the uploads directory if present.
    """
    safe_name = sanitize_filename(filename)
    vectorstore = request.app.state.vectorstore

    deleted_count = vectorstore.delete_by_source(safe_name)

    if deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Document '{safe_name}' not found in the knowledge base.",
        )

    # Safely clean up uploaded file from disk if it exists
    upload_root = Path(UPLOAD_DIR).resolve()
    file_path = (upload_root / safe_name).resolve()
    if str(file_path).startswith(str(upload_root)) and file_path.is_file():
        try:
            file_path.unlink(missing_ok=True)
        except OSError:
            pass

    return {
        "filename": safe_name,
        "chunks_deleted": deleted_count,
        "status": "deleted",
    }
