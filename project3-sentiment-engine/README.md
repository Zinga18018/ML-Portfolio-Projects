# Real-time Sentiment Engine

Production sentiment analysis API powered by DistilBERT. Handles single, batch, and comparison inference with confidence scores and aggregate analytics.

## Stack
- **Model**: distilbert-base-uncased-finetuned-sst-2-english (67M parameters)
- **API**: FastAPI + Uvicorn
- **Inference**: HuggingFace pipeline with CUDA acceleration

## Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/analyze` | Single text sentiment |
| POST | `/analyze/batch` | Batch analysis (up to 100 texts) |
| POST | `/analyze/analytics` | Batch with aggregate stats |
| POST | `/compare` | Compare sentiment of two texts |

## Run
```bash
pip install -r requirements.txt
python app.py
# API docs: http://localhost:8003/docs
```

## Example
```bash
curl -X POST http://localhost:8003/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "This product is absolutely fantastic!"}'
```
