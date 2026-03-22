# AI Code Review Agent

TinyLlama-1.1B powered code review system. Feed it code diffs and get line-by-line reviews with bug detection, style suggestions, and security warnings.

## Stack
- **Model**: TinyLlama/TinyLlama-1.1B-Chat-v1.0 (1.1B parameters)
- **API**: FastAPI + Uvicorn
- **Inference**: PyTorch with CUDA acceleration
- **Streaming**: Server-Sent Events for real-time token output

## Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check + GPU info |
| POST | `/review` | Single code review (blocking) |
| POST | `/review/stream` | Streaming code review (SSE) |
| POST | `/review/batch` | Review multiple snippets |

## Run
```bash
pip install -r requirements.txt
python app.py
# API docs: http://localhost:8001/docs
```

## Example
```bash
curl -X POST http://localhost:8001/review \
  -H "Content-Type: application/json" \
  -d '{"code": "def add(a, b):\n    return a + b", "language": "python"}'
```
