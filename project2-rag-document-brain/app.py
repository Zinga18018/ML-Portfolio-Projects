"""
RAG Document Brain
==================
Retrieval-Augmented Generation pipeline. Upload documents, chunk and embed
them via Sentence-Transformers into ChromaDB. Ask questions and get
grounded answers with source citations.
"""

import hashlib
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Optional

import chromadb
import torch
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# -- Config --
EMBED_MODEL = "all-MiniLM-L6-v2"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K = 5
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# -- Init --
app = FastAPI(title="RAG Document Brain", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Load embedding model
logger.info(f"Loading embedding model: {EMBED_MODEL}")
device = "cuda" if torch.cuda.is_available() else "cpu"
embed_model = SentenceTransformer(EMBED_MODEL, device=device)
logger.info(f"Embedding model loaded on {device}")

# ChromaDB
chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection(
    name="documents",
    metadata={"hnsw:space": "cosine"},
)


# -- Schemas --
class QueryRequest(BaseModel):
    question: str
    top_k: int = TOP_K
    collection_name: str = "documents"


class QueryResult(BaseModel):
    answer: str
    sources: list[dict]
    query_time_ms: float
    total_chunks: int


class IngestResponse(BaseModel):
    filename: str
    chunks_created: int
    total_chars: int
    ingest_time_ms: float


# -- Text Processing --
def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks."""
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
        i += chunk_size - overlap
    return chunks


def extract_text(content: bytes, filename: str) -> str:
    """Extract text from uploaded file."""
    # Simple text extraction - handles .txt, .md, .py, .js, etc.
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("latin-1")


# -- Endpoints --
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "embed_model": EMBED_MODEL,
        "device": device,
        "total_documents": collection.count(),
    }


@app.post("/ingest", response_model=IngestResponse)
async def ingest_document(file: UploadFile = File(...)):
    """Upload and ingest a document into the vector store."""
    start = time.perf_counter()

    content = await file.read()
    text = extract_text(content, file.filename)

    if not text.strip():
        raise HTTPException(400, "Empty or unreadable file")

    chunks = chunk_text(text)
    if not chunks:
        raise HTTPException(400, "No content chunks generated")

    # Generate embeddings
    embeddings = embed_model.encode(chunks, show_progress_bar=False).tolist()

    # Store in ChromaDB
    ids = [f"{file.filename}_{i}_{uuid.uuid4().hex[:8]}" for i in range(len(chunks))]
    metadatas = [{"filename": file.filename, "chunk_idx": i, "chunk_total": len(chunks)} for i in range(len(chunks))]

    collection.add(
        documents=chunks,
        embeddings=embeddings,
        ids=ids,
        metadatas=metadatas,
    )

    elapsed = (time.perf_counter() - start) * 1000
    logger.info(f"Ingested {file.filename}: {len(chunks)} chunks in {elapsed:.0f}ms")

    return IngestResponse(
        filename=file.filename,
        chunks_created=len(chunks),
        total_chars=len(text),
        ingest_time_ms=round(elapsed, 1),
    )


@app.post("/ingest/text")
async def ingest_text(body: dict):
    """Ingest raw text directly."""
    text = body.get("text", "")
    title = body.get("title", "untitled")

    if not text.strip():
        raise HTTPException(400, "Empty text")

    start = time.perf_counter()
    chunks = chunk_text(text)
    embeddings = embed_model.encode(chunks, show_progress_bar=False).tolist()

    ids = [f"{title}_{i}_{uuid.uuid4().hex[:8]}" for i in range(len(chunks))]
    metadatas = [{"filename": title, "chunk_idx": i, "chunk_total": len(chunks)} for i in range(len(chunks))]

    collection.add(documents=chunks, embeddings=embeddings, ids=ids, metadatas=metadatas)

    elapsed = (time.perf_counter() - start) * 1000
    return {"title": title, "chunks": len(chunks), "time_ms": round(elapsed, 1)}


@app.post("/query", response_model=QueryResult)
async def query_documents(req: QueryRequest):
    """Semantic search over ingested documents."""
    if collection.count() == 0:
        raise HTTPException(400, "No documents ingested yet. Upload documents first.")

    start = time.perf_counter()

    # Embed query
    query_embedding = embed_model.encode([req.question]).tolist()

    # Search
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=min(req.top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    elapsed = (time.perf_counter() - start) * 1000

    # Build sources
    sources = []
    context_parts = []
    for i in range(len(results["documents"][0])):
        doc = results["documents"][0][i]
        meta = results["metadatas"][0][i]
        dist = results["distances"][0][i]
        similarity = 1 - dist  # cosine distance to similarity

        sources.append({
            "text": doc[:300] + ("..." if len(doc) > 300 else ""),
            "filename": meta.get("filename", "unknown"),
            "chunk_idx": meta.get("chunk_idx", 0),
            "similarity": round(similarity, 4),
        })
        context_parts.append(doc)

    # Build answer from retrieved context
    context = "\n\n---\n\n".join(context_parts)
    answer = f"Based on {len(sources)} relevant passages from your documents:\n\n"
    for i, src in enumerate(sources):
        answer += f"[{i+1}] From '{src['filename']}' (relevance: {src['similarity']:.0%}):\n"
        answer += f"   {src['text'][:200]}...\n\n"

    return QueryResult(
        answer=answer,
        sources=sources,
        query_time_ms=round(elapsed, 1),
        total_chunks=collection.count(),
    )


@app.get("/documents")
async def list_documents():
    """List all ingested documents."""
    if collection.count() == 0:
        return {"documents": [], "total_chunks": 0}

    all_data = collection.get(include=["metadatas"])
    filenames = set()
    for meta in all_data["metadatas"]:
        filenames.add(meta.get("filename", "unknown"))

    return {
        "documents": sorted(filenames),
        "total_chunks": collection.count(),
    }


@app.delete("/documents")
async def clear_documents():
    """Clear all documents from the vector store."""
    global collection
    chroma_client.delete_collection("documents")
    collection = chroma_client.create_collection(name="documents", metadata={"hnsw:space": "cosine"})
    return {"status": "cleared", "total_chunks": 0}


@app.post("/similar")
async def find_similar(body: dict):
    """Find documents similar to given text."""
    text = body.get("text", "")
    top_k = body.get("top_k", 5)

    if not text.strip():
        raise HTTPException(400, "Empty text")

    embedding = embed_model.encode([text]).tolist()
    results = collection.query(
        query_embeddings=embedding,
        n_results=min(top_k, max(collection.count(), 1)),
        include=["documents", "metadatas", "distances"],
    )

    similar = []
    for i in range(len(results["documents"][0])):
        similar.append({
            "text": results["documents"][0][i][:300],
            "filename": results["metadatas"][0][i].get("filename"),
            "similarity": round(1 - results["distances"][0][i], 4),
        })

    return {"results": similar}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8002, reload=True)
