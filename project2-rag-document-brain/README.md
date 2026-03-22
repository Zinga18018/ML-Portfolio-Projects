# RAG Document Brain

Retrieval-Augmented Generation pipeline. Upload documents, chunk and embed them via Sentence-Transformers into ChromaDB. Ask natural language questions and get grounded answers with source citations.

## Stack
- **Embeddings**: all-MiniLM-L6-v2 (384-dimensional)
- **Vector Store**: ChromaDB (cosine similarity)
- **API**: FastAPI + Uvicorn
- **Search**: Semantic top-K retrieval with similarity scores

## Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check + document count |
| POST | `/ingest` | Upload and embed a document |
| POST | `/ingest/text` | Ingest raw text directly |
| POST | `/query` | Semantic search + answer generation |
| GET | `/documents` | List ingested documents |
| DELETE | `/documents` | Clear all documents |
| POST | `/similar` | Find similar text passages |

## Run
```bash
pip install -r requirements.txt
python app.py
# API docs: http://localhost:8002/docs
```

## Example
```bash
# Ingest a document
curl -X POST http://localhost:8002/ingest -F "file=@readme.txt"

# Query
curl -X POST http://localhost:8002/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is this project about?"}'
```
