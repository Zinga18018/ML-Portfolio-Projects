"""
Real-time Sentiment Engine
===========================
Production sentiment analysis API powered by DistilBERT.
Handles single, batch, and streaming inference with confidence scores.
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import Optional

import torch
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

MODEL_ID = "distilbert-base-uncased-finetuned-sst-2-english"
sentiment_pipeline = None
device_name = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global sentiment_pipeline, device_name
    logger.info(f"Loading {MODEL_ID}...")
    device_idx = 0 if torch.cuda.is_available() else -1
    device_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"

    sentiment_pipeline = pipeline(
        "sentiment-analysis",
        model=MODEL_ID,
        device=device_idx,
        truncation=True,
        max_length=512,
    )
    logger.info(f"Model loaded on {device_name}")
    yield


app = FastAPI(title="Real-time Sentiment Engine", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class SentimentRequest(BaseModel):
    text: str
    return_all_scores: bool = False


class SentimentResult(BaseModel):
    text: str
    label: str
    score: float
    inference_ms: float


class BatchRequest(BaseModel):
    texts: list[str]


class BatchResult(BaseModel):
    results: list[SentimentResult]
    total_inference_ms: float
    avg_inference_ms: float
    throughput_texts_per_sec: float


class AnalyticsResult(BaseModel):
    total_texts: int
    positive_count: int
    negative_count: int
    positive_ratio: float
    avg_confidence: float
    most_positive: dict
    most_negative: dict
    inference_ms: float


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "model": MODEL_ID,
        "device": device_name,
        "params": "67M",
    }


@app.post("/analyze", response_model=SentimentResult)
async def analyze_sentiment(req: SentimentRequest):
    """Analyze sentiment of a single text."""
    if not sentiment_pipeline:
        raise HTTPException(503, "Model not loaded")

    start = time.perf_counter()
    result = sentiment_pipeline(req.text)[0]
    elapsed = (time.perf_counter() - start) * 1000

    return SentimentResult(
        text=req.text[:200],
        label=result["label"],
        score=round(result["score"], 4),
        inference_ms=round(elapsed, 1),
    )


@app.post("/analyze/batch", response_model=BatchResult)
async def analyze_batch(req: BatchRequest):
    """Analyze sentiment of multiple texts at once."""
    if not sentiment_pipeline:
        raise HTTPException(503, "Model not loaded")
    if len(req.texts) > 100:
        raise HTTPException(400, "Max 100 texts per batch")

    start = time.perf_counter()
    results = sentiment_pipeline(req.texts)
    total_ms = (time.perf_counter() - start) * 1000

    items = []
    for text, result in zip(req.texts, results):
        items.append(SentimentResult(
            text=text[:200],
            label=result["label"],
            score=round(result["score"], 4),
            inference_ms=round(total_ms / len(req.texts), 1),
        ))

    return BatchResult(
        results=items,
        total_inference_ms=round(total_ms, 1),
        avg_inference_ms=round(total_ms / len(req.texts), 1),
        throughput_texts_per_sec=round(len(req.texts) / (total_ms / 1000), 1),
    )


@app.post("/analyze/analytics", response_model=AnalyticsResult)
async def analyze_with_analytics(req: BatchRequest):
    """Batch analysis with aggregate analytics."""
    if not sentiment_pipeline:
        raise HTTPException(503, "Model not loaded")
    if len(req.texts) > 100:
        raise HTTPException(400, "Max 100 texts per batch")

    start = time.perf_counter()
    results = sentiment_pipeline(req.texts)
    elapsed = (time.perf_counter() - start) * 1000

    pos_count = sum(1 for r in results if r["label"] == "POSITIVE")
    neg_count = len(results) - pos_count
    avg_conf = sum(r["score"] for r in results) / len(results)

    # Find extremes
    pos_results = [(t, r) for t, r in zip(req.texts, results) if r["label"] == "POSITIVE"]
    neg_results = [(t, r) for t, r in zip(req.texts, results) if r["label"] == "NEGATIVE"]

    most_pos = max(pos_results, key=lambda x: x[1]["score"]) if pos_results else (req.texts[0], results[0])
    most_neg = max(neg_results, key=lambda x: x[1]["score"]) if neg_results else (req.texts[0], results[0])

    return AnalyticsResult(
        total_texts=len(req.texts),
        positive_count=pos_count,
        negative_count=neg_count,
        positive_ratio=round(pos_count / len(req.texts), 4),
        avg_confidence=round(avg_conf, 4),
        most_positive={"text": most_pos[0][:200], "score": most_pos[1]["score"]},
        most_negative={"text": most_neg[0][:200], "score": most_neg[1]["score"]},
        inference_ms=round(elapsed, 1),
    )


@app.post("/compare")
async def compare_texts(body: dict):
    """Compare sentiment between two texts."""
    text_a = body.get("text_a", "")
    text_b = body.get("text_b", "")

    if not text_a or not text_b:
        raise HTTPException(400, "Both text_a and text_b required")

    start = time.perf_counter()
    results = sentiment_pipeline([text_a, text_b])
    elapsed = (time.perf_counter() - start) * 1000

    score_a = results[0]["score"] if results[0]["label"] == "POSITIVE" else -results[0]["score"]
    score_b = results[1]["score"] if results[1]["label"] == "POSITIVE" else -results[1]["score"]

    return {
        "text_a": {"text": text_a[:200], "label": results[0]["label"], "score": results[0]["score"]},
        "text_b": {"text": text_b[:200], "label": results[1]["label"], "score": results[1]["score"]},
        "more_positive": "text_a" if score_a > score_b else "text_b",
        "sentiment_gap": round(abs(score_a - score_b), 4),
        "inference_ms": round(elapsed, 1),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8003, reload=True)
