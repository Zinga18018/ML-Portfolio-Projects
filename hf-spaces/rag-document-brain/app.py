"""
RAG Document Brain -- Hugging Face Spaces (Docker)
Semantic search + document Q&A via Sentence-Transformers + ChromaDB.
Supports CSV parsing with column-aware indexing and PDF ingestion.
"""

import csv
import io
import time
import uuid
import re
from collections import Counter
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import chromadb
import fitz  # PyMuPDF
import torch
from sentence_transformers import SentenceTransformer
from transformers import AutoModelForCausalLM, AutoTokenizer

app = FastAPI()

EMBED_MODEL = "all-MiniLM-L6-v2"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

print(f"Loading {EMBED_MODEL}...")
embed_model = SentenceTransformer(EMBED_MODEL, device="cpu")
print("Embedding model loaded.")

LLM_ID = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
print(f"Loading {LLM_ID}...")
llm_tokenizer = AutoTokenizer.from_pretrained(LLM_ID)
llm_model = AutoModelForCausalLM.from_pretrained(LLM_ID, torch_dtype=torch.float32)
llm_model.eval()
print("LLM loaded.")

chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection(
    name="documents",
    metadata={"hnsw:space": "cosine"},
)

STOPWORDS = set("the a an and or but in on at to for of is it this that with as by from are was were be been".split())


def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
        i += chunk_size - overlap
    return chunks


def extract_top_words(text, n=40):
    words = re.findall(r'[a-zA-Z]{3,}', text.lower())
    filtered = [w for w in words if w not in STOPWORDS]
    counts = Counter(filtered)
    return [{"word": w, "count": c} for w, c in counts.most_common(n)]


class IngestRequest(BaseModel):
    text: str
    title: str = "untitled"


class QueryRequest(BaseModel):
    question: str
    top_k: int = 5


class AskRequest(BaseModel):
    question: str
    top_k: int = 3
    max_tokens: int = 300


@app.post("/api/ingest")
def ingest_text(req: IngestRequest):
    if not req.text.strip():
        return {"error": "Empty text."}

    title = req.title.strip() or "untitled"
    start = time.perf_counter()
    chunks = chunk_text(req.text)
    embeddings = embed_model.encode(chunks, show_progress_bar=False).tolist()

    ids = [f"{title}_{i}_{uuid.uuid4().hex[:8]}" for i in range(len(chunks))]
    metadatas = [{"filename": title, "chunk_idx": i, "chunk_total": len(chunks)} for i in range(len(chunks))]

    collection.add(documents=chunks, embeddings=embeddings, ids=ids, metadatas=metadatas)
    ms = (time.perf_counter() - start) * 1000

    return {
        "title": title,
        "chunks": len(chunks),
        "characters": len(req.text),
        "ms": round(ms, 1),
        "total_docs": collection.count(),
    }


@app.post("/api/upload")
async def ingest_file(file: UploadFile = File(...)):
    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    title = file.filename or "uploaded-file"
    req = IngestRequest(text=text, title=title)
    return ingest_text(req)


@app.post("/api/csv/preview")
async def csv_preview(file: UploadFile = File(...)):
    """Parse CSV and return headers + first 10 rows for preview."""
    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader = csv.reader(io.StringIO(text))
    rows = []
    for row in reader:
        rows.append(row)
        if len(rows) > 11:
            break

    if not rows:
        return {"error": "Empty CSV file."}

    headers = rows[0]
    preview_rows = rows[1:11]
    total_lines = text.count('\n')

    return {
        "filename": file.filename,
        "headers": headers,
        "preview": preview_rows,
        "total_rows": total_lines,
        "columns": len(headers),
    }


@app.post("/api/csv/ingest")
async def csv_ingest(file: UploadFile = File(...), columns: str = Form("")):
    """Ingest CSV with selected columns only."""
    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []
    selected = [c.strip() for c in columns.split(",") if c.strip()] if columns else headers

    title = file.filename or "csv-upload"
    all_text_parts = []
    row_count = 0

    for row in reader:
        parts = [f"{col}: {row.get(col, '')}" for col in selected if row.get(col, '').strip()]
        if parts:
            all_text_parts.append(" | ".join(parts))
            row_count += 1

    combined_text = "\n".join(all_text_parts)
    if not combined_text.strip():
        return {"error": "No data found in selected columns."}

    start = time.perf_counter()
    chunks = chunk_text(combined_text)
    embeddings = embed_model.encode(chunks, show_progress_bar=False).tolist()

    ids = [f"{title}_{i}_{uuid.uuid4().hex[:8]}" for i in range(len(chunks))]
    metadatas = [{"filename": title, "chunk_idx": i, "chunk_total": len(chunks), "type": "csv"} for i in range(len(chunks))]

    collection.add(documents=chunks, embeddings=embeddings, ids=ids, metadatas=metadatas)
    ms = (time.perf_counter() - start) * 1000

    return {
        "title": title,
        "rows_indexed": row_count,
        "columns_used": selected,
        "chunks": len(chunks),
        "ms": round(ms, 1),
        "total_docs": collection.count(),
    }


@app.post("/api/pdf/preview")
async def pdf_preview(file: UploadFile = File(...)):
    """Extract text from PDF and return page-level preview."""
    content = await file.read()
    try:
        doc = fitz.open(stream=content, filetype="pdf")
    except Exception as e:
        return {"error": f"Failed to parse PDF: {str(e)}"}

    pages = []
    total_chars = 0
    for i, page in enumerate(doc):
        text = page.get_text("text").strip()
        total_chars += len(text)
        pages.append({
            "page": i + 1,
            "chars": len(text),
            "preview": text[:300] + ("..." if len(text) > 300 else ""),
        })

    return {
        "filename": file.filename,
        "total_pages": len(doc),
        "total_chars": total_chars,
        "pages": pages,
    }


@app.post("/api/pdf/ingest")
async def pdf_ingest(
    file: UploadFile = File(...),
    page_start: int = Form(1),
    page_end: int = Form(0),
):
    """Ingest PDF pages into the vector store. page_end=0 means all pages."""
    content = await file.read()
    try:
        doc = fitz.open(stream=content, filetype="pdf")
    except Exception as e:
        return {"error": f"Failed to parse PDF: {str(e)}"}

    title = file.filename or "uploaded.pdf"
    end = page_end if page_end > 0 else len(doc)
    start_idx = max(0, page_start - 1)
    end_idx = min(end, len(doc))

    all_text_parts = []
    pages_processed = 0
    for i in range(start_idx, end_idx):
        page_text = doc[i].get_text("text").strip()
        if page_text:
            all_text_parts.append(f"[Page {i + 1}]\n{page_text}")
            pages_processed += 1

    combined_text = "\n\n".join(all_text_parts)
    if not combined_text.strip():
        return {"error": "No extractable text found in selected pages."}

    start = time.perf_counter()
    chunks = chunk_text(combined_text)
    embeddings = embed_model.encode(chunks, show_progress_bar=False).tolist()

    ids = [f"{title}_{i}_{uuid.uuid4().hex[:8]}" for i in range(len(chunks))]
    metadatas = [
        {"filename": title, "chunk_idx": i, "chunk_total": len(chunks), "type": "pdf"}
        for i in range(len(chunks))
    ]

    collection.add(documents=chunks, embeddings=embeddings, ids=ids, metadatas=metadatas)
    ms = (time.perf_counter() - start) * 1000

    return {
        "title": title,
        "pages_processed": pages_processed,
        "page_range": f"{start_idx + 1}-{end_idx}",
        "total_pages": len(doc),
        "characters": len(combined_text),
        "chunks": len(chunks),
        "ms": round(ms, 1),
        "total_docs": collection.count(),
    }


@app.post("/api/query")
def query_docs(req: QueryRequest):
    if not req.question.strip():
        return {"error": "Empty question."}
    if collection.count() == 0:
        return {"error": "No documents ingested yet."}

    start = time.perf_counter()
    query_embedding = embed_model.encode([req.question]).tolist()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=min(req.top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )
    ms = (time.perf_counter() - start) * 1000

    matches = []
    for i in range(len(results["documents"][0])):
        doc = results["documents"][0][i]
        meta = results["metadatas"][0][i]
        dist = results["distances"][0][i]
        matches.append({
            "rank": i + 1,
            "source": meta.get("filename", "unknown"),
            "similarity": round(1 - dist, 4),
            "preview": doc[:300],
        })

    return {"question": req.question, "ms": round(ms, 1), "results": matches}


@app.post("/api/ask")
def ask(req: AskRequest):
    """Retrieve relevant chunks and generate a natural language answer."""
    if not req.question.strip():
        return {"error": "Empty question."}
    if collection.count() == 0:
        return {"error": "No documents ingested yet. Upload a PDF, CSV, or text first."}

    # Step 1: Retrieve
    retrieve_start = time.perf_counter()
    query_embedding = embed_model.encode([req.question]).tolist()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=min(req.top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )
    retrieve_ms = (time.perf_counter() - retrieve_start) * 1000

    # Build context from retrieved chunks
    context_parts = []
    sources = []
    for i in range(len(results["documents"][0])):
        doc = results["documents"][0][i]
        meta = results["metadatas"][0][i]
        dist = results["distances"][0][i]
        sim = round(1 - dist, 4)
        source = meta.get("filename", "unknown")
        context_parts.append(doc[:600])
        sources.append({"source": source, "similarity": sim})

    context = "\n\n".join(context_parts)

    # Step 2: Generate answer using TinyLlama
    system_prompt = (
        "You are a helpful research assistant. Answer the user's question based ONLY on "
        "the provided context. If the context doesn't contain enough information, say so. "
        "Be clear, concise, and cite which parts of the context support your answer."
    )
    prompt = (
        f"<|system|>\n{system_prompt}</s>\n"
        f"<|user|>\nContext from documents:\n{context}\n\n"
        f"Question: {req.question}</s>\n"
        f"<|assistant|>\n"
    )

    inputs = llm_tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048)

    gen_start = time.perf_counter()
    with torch.no_grad():
        out = llm_model.generate(
            **inputs,
            max_new_tokens=req.max_tokens,
            temperature=0.7,
            top_p=0.9,
            do_sample=True,
            repetition_penalty=1.15,
            pad_token_id=llm_tokenizer.eos_token_id,
            use_cache=True,
        )
    gen_ms = (time.perf_counter() - gen_start) * 1000

    new_ids = out[0][inputs["input_ids"].shape[1]:]
    answer = llm_tokenizer.decode(new_ids, skip_special_tokens=True).strip()
    tokens = len(new_ids)

    return {
        "question": req.question,
        "answer": answer,
        "sources": sources,
        "tokens": tokens,
        "retrieve_ms": round(retrieve_ms, 1),
        "generate_ms": round(gen_ms, 1),
        "total_ms": round(retrieve_ms + gen_ms, 1),
    }


@app.get("/api/status")
def get_status():
    if collection.count() == 0:
        return {"total_chunks": 0, "documents": [], "model": EMBED_MODEL, "top_words": []}

    all_data = collection.get(include=["metadatas", "documents"])
    filenames = sorted(set(m.get("filename", "unknown") for m in all_data["metadatas"]))
    all_text = " ".join(all_data["documents"])
    top_words = extract_top_words(all_text, 40)

    return {
        "total_chunks": collection.count(),
        "documents": filenames,
        "model": EMBED_MODEL,
        "top_words": top_words,
    }


@app.post("/api/clear")
def clear_all():
    global collection
    chroma_client.delete_collection("documents")
    collection = chroma_client.get_or_create_collection(name="documents", metadata={"hnsw:space": "cosine"})
    return {"status": "cleared"}


app.mount("/", StaticFiles(directory="static", html=True), name="static")
