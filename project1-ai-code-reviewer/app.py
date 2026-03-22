"""
AI Code Review Agent
====================
TinyLlama-1.1B powered code review system.
Feed it code diffs and get line-by-line reviews with bug detection,
style suggestions, and security warnings. Served via FastAPI.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Optional

import torch
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
from threading import Thread

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# -- Global model state --
model = None
tokenizer = None
device = None

MODEL_ID = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model on startup."""
    global model, tokenizer, device
    logger.info(f"Loading {MODEL_ID}...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Device: {device}")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        device_map="auto" if device == "cuda" else None,
    )
    if device == "cpu":
        model = model.to(device)

    logger.info("Model loaded successfully.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="AI Code Review Agent",
    description="TinyLlama-powered code review system",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ReviewRequest(BaseModel):
    code: str
    language: str = "python"
    focus: str = "general"  # general, security, performance, style
    max_tokens: int = 512


class ReviewResponse(BaseModel):
    review: str
    language: str
    focus: str
    inference_time_ms: float
    model: str
    device: str


SYSTEM_PROMPT = """You are an expert code reviewer. Analyze the code below and provide:
1. **Bugs & Issues**: Any logical errors, potential crashes, or incorrect behavior
2. **Security**: SQL injection, XSS, command injection, hardcoded secrets, etc.
3. **Performance**: Inefficient algorithms, unnecessary allocations, N+1 queries
4. **Style**: Naming conventions, code organization, readability improvements
5. **Summary**: One-line verdict (APPROVE / REQUEST_CHANGES / NEEDS_DISCUSSION)

Be specific. Reference line numbers. Be concise but thorough."""


def build_prompt(code: str, language: str, focus: str) -> str:
    focus_instruction = {
        "general": "Review all aspects of this code.",
        "security": "Focus primarily on security vulnerabilities and data safety.",
        "performance": "Focus primarily on performance bottlenecks and optimization.",
        "style": "Focus primarily on code style, readability, and best practices.",
    }.get(focus, "Review all aspects of this code.")

    return f"""<|system|>
{SYSTEM_PROMPT}
{focus_instruction}</s>
<|user|>
Review this {language} code:

```{language}
{code}
```</s>
<|assistant|>
"""


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "model": MODEL_ID,
        "device": str(device),
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    }


@app.post("/review", response_model=ReviewResponse)
async def review_code(req: ReviewRequest):
    """Generate a code review (non-streaming)."""
    if model is None:
        raise HTTPException(503, "Model not loaded yet")

    prompt = build_prompt(req.code, req.language, req.focus)
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048).to(device)

    start = time.perf_counter()
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=req.max_tokens,
            temperature=0.7,
            top_p=0.9,
            do_sample=True,
            repetition_penalty=1.1,
            pad_token_id=tokenizer.eos_token_id,
        )
    elapsed = (time.perf_counter() - start) * 1000

    response_ids = outputs[0][inputs["input_ids"].shape[1]:]
    review_text = tokenizer.decode(response_ids, skip_special_tokens=True)

    return ReviewResponse(
        review=review_text.strip(),
        language=req.language,
        focus=req.focus,
        inference_time_ms=round(elapsed, 1),
        model=MODEL_ID,
        device=str(device),
    )


@app.post("/review/stream")
async def review_code_stream(req: ReviewRequest):
    """Generate a code review with streaming response."""
    if model is None:
        raise HTTPException(503, "Model not loaded yet")

    prompt = build_prompt(req.code, req.language, req.focus)
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048).to(device)

    streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)

    gen_kwargs = {
        **{k: v for k, v in inputs.items()},
        "max_new_tokens": req.max_tokens,
        "temperature": 0.7,
        "top_p": 0.9,
        "do_sample": True,
        "repetition_penalty": 1.1,
        "pad_token_id": tokenizer.eos_token_id,
        "streamer": streamer,
    }

    thread = Thread(target=lambda: model.generate(**gen_kwargs))
    thread.start()

    async def event_stream():
        for text in streamer:
            yield f"data: {text}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/review/batch")
async def review_batch(requests: list[ReviewRequest]):
    """Review multiple code snippets."""
    results = []
    for req in requests[:5]:  # cap at 5
        prompt = build_prompt(req.code, req.language, req.focus)
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048).to(device)
        start = time.perf_counter()
        with torch.no_grad():
            outputs = model.generate(
                **inputs, max_new_tokens=req.max_tokens,
                temperature=0.7, top_p=0.9, do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
            )
        elapsed = (time.perf_counter() - start) * 1000
        response_ids = outputs[0][inputs["input_ids"].shape[1]:]
        review_text = tokenizer.decode(response_ids, skip_special_tokens=True)
        results.append(ReviewResponse(
            review=review_text.strip(), language=req.language, focus=req.focus,
            inference_time_ms=round(elapsed, 1), model=MODEL_ID, device=str(device),
        ))
    return results


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8001, reload=True)
