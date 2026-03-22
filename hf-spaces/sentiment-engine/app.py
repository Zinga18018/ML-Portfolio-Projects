import time
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from transformers import pipeline

app = FastAPI()

print("Loading DistilBERT...")
classifier = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english", device=-1, truncation=True, max_length=512)
print("Ready.")

# Emotion keywords mapped to pseudo-scores (no second model needed -- heuristic overlay)
EMOTION_KEYWORDS = {
    "joy": ["happy", "great", "amazing", "love", "wonderful", "fantastic", "excellent", "awesome", "delightful", "thrilled", "excited", "cheerful", "pleased", "glad"],
    "anger": ["angry", "furious", "hate", "annoyed", "irritated", "outraged", "mad", "rage", "frustrated", "infuriated", "hostile", "bitter"],
    "sadness": ["sad", "depressed", "miserable", "unhappy", "heartbroken", "gloomy", "disappointed", "tragic", "grief", "lonely", "hopeless", "melancholy"],
    "fear": ["afraid", "scared", "terrified", "anxious", "worried", "panic", "dread", "frightened", "nervous", "alarmed", "uneasy", "horror"],
    "surprise": ["surprised", "shocked", "unexpected", "astonished", "amazed", "stunned", "unbelievable", "startled", "wow", "incredible"],
    "disgust": ["disgusting", "gross", "revolting", "nasty", "horrible", "repulsive", "vile", "sickening", "appalling", "dreadful"],
}


def compute_emotions(text):
    words = text.lower().split()
    scores = {}
    for emotion, keywords in EMOTION_KEYWORDS.items():
        count = sum(1 for w in words for kw in keywords if kw in w)
        scores[emotion] = min(count / max(len(words) * 0.15, 1), 1.0)

    total = sum(scores.values())
    if total > 0:
        scores = {k: round(v / total, 4) for k, v in scores.items()}
    else:
        scores = {k: round(1 / 6, 4) for k in scores}
    return scores


class TextInput(BaseModel):
    text: str


class BatchInput(BaseModel):
    texts: list[str]


class CompareInput(BaseModel):
    text_a: str
    text_b: str


@app.post("/api/analyze")
def analyze(req: TextInput):
    start = time.perf_counter()
    result = classifier(req.text)[0]
    ms = (time.perf_counter() - start) * 1000
    emotions = compute_emotions(req.text)
    return {
        "label": result["label"],
        "score": round(result["score"], 6),
        "ms": round(ms, 1),
        "emotions": emotions,
    }


@app.post("/api/batch")
def batch(req: BatchInput):
    texts = req.texts[:50]
    start = time.perf_counter()
    results = classifier(texts)
    ms = (time.perf_counter() - start) * 1000
    items = [{"text": t[:120], "label": r["label"], "score": round(r["score"], 4)} for t, r in zip(texts, results)]
    pos = sum(1 for r in results if r["label"] == "POSITIVE")
    return {
        "results": items,
        "stats": {
            "total": len(items), "positive": pos, "negative": len(items) - pos,
            "ratio": round(pos / len(items), 4), "total_ms": round(ms, 1),
            "avg_ms": round(ms / len(items), 1),
            "throughput": round(len(items) / (ms / 1000), 1),
        }
    }


@app.post("/api/compare")
def compare(req: CompareInput):
    start = time.perf_counter()
    results = classifier([req.text_a, req.text_b])
    ms = (time.perf_counter() - start) * 1000
    def signed(r): return r["score"] if r["label"] == "POSITIVE" else -r["score"]
    sa, sb = signed(results[0]), signed(results[1])
    return {
        "a": {"label": results[0]["label"], "score": round(results[0]["score"], 4)},
        "b": {"label": results[1]["label"], "score": round(results[1]["score"], 4)},
        "winner": "A" if sa > sb else "B",
        "gap": round(abs(sa - sb), 4), "ms": round(ms, 1),
    }


@app.post("/api/live")
def live_analyze(req: TextInput):
    """Lightweight endpoint for real-time typing analysis."""
    if len(req.text.strip()) < 3:
        return {"label": "NEUTRAL", "score": 0.5, "ms": 0}
    start = time.perf_counter()
    result = classifier(req.text)[0]
    ms = (time.perf_counter() - start) * 1000
    signed_score = result["score"] if result["label"] == "POSITIVE" else -result["score"]
    return {"label": result["label"], "score": round(result["score"], 6), "signed": round(signed_score, 6), "ms": round(ms, 1)}


app.mount("/", StaticFiles(directory="static", html=True), name="static")
