"""
Ingestion service — parses documents, chunks text, and stores embeddings.
"""

import os
import uuid
from typing import Optional

import pdfplumber
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import CHUNK_SIZE, CHUNK_OVERLAP
from app.services.vectorstore import VectorStore


SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}


class IngestionService:
    """Handles document parsing, chunking, and ingestion into the vector store."""

    def __init__(self, vectorstore: VectorStore):
        self.vectorstore = vectorstore
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def parse_file(self, filepath: str) -> str:
        """Extract raw text from a supported file."""
        ext = os.path.splitext(filepath)[1].lower()

        if ext not in SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type: '{ext}'. "
                f"Supported types: {', '.join(SUPPORTED_EXTENSIONS)}"
            )

        if ext == ".pdf":
            return self._parse_pdf(filepath)
        else:
            return self._parse_text(filepath)

    def _parse_pdf(self, filepath: str) -> str:
        """Extract text from a PDF file using pdfplumber."""
        pages = []
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
        return "\n\n".join(pages)

    def _parse_text(self, filepath: str) -> str:
        """Read text from a plain text or markdown file."""
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read().strip()

    def ingest_file(self, filepath: str, filename: Optional[str] = None) -> int:
        """
        Parse, chunk, and store a single file.
        Returns the number of chunks created.
        """
        if filename is None:
            filename = os.path.basename(filepath)

        # Parse the file
        text = self.parse_file(filepath)
        if not text.strip():
            return 0

        # Split into chunks
        chunks = self.splitter.split_text(text)
        if not chunks:
            return 0

        # Build IDs and metadata for each chunk
        ids = [f"{filename}_chunk_{i}_{uuid.uuid4().hex[:8]}" for i in range(len(chunks))]
        metadatas = [
            {
                "source": filename,
                "chunk_index": i,
                "total_chunks": len(chunks),
            }
            for i in range(len(chunks))
        ]

        # Store in the vector store
        self.vectorstore.add_documents(
            ids=ids,
            documents=chunks,
            metadatas=metadatas,
        )

        return len(chunks)

    def ingest_directory(self, directory: str) -> dict[str, dict]:
        """
        Ingest all supported files from a directory.
        Returns a dict of filename → {chunks, status}.
        """
        results: dict[str, dict] = {}

        if not os.path.isdir(directory):
            return results

        for filename in sorted(os.listdir(directory)):
            ext = os.path.splitext(filename)[1].lower()
            if ext not in SUPPORTED_EXTENSIONS:
                continue

            filepath = os.path.join(directory, filename)
            try:
                chunk_count = self.ingest_file(filepath, filename)
                results[filename] = {"chunks": chunk_count, "status": "success"}
            except Exception as e:
                results[filename] = {"chunks": 0, "status": f"error: {str(e)}"}

        return results
