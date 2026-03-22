"""
Neural Image Captioner
======================
Vision-Language model that generates natural language descriptions of images.
Uses ViT encoder + GPT-2 decoder (VisionEncoderDecoderModel) from HuggingFace.
Upload an image and get a detailed caption.
"""

import io
import logging
import time
from contextlib import asynccontextmanager

import torch
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from pydantic import BaseModel
from transformers import (
    VisionEncoderDecoderModel,
    ViTImageProcessor,
    AutoTokenizer,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

MODEL_ID = "nlpconnect/vit-gpt2-image-captioning"

model = None
feature_extractor = None
tokenizer = None
device = None
gen_kwargs = {"max_length": 64, "num_beams": 4, "num_return_sequences": 1}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, feature_extractor, tokenizer, device
    logger.info(f"Loading {MODEL_ID}...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = VisionEncoderDecoderModel.from_pretrained(MODEL_ID)
    feature_extractor = ViTImageProcessor.from_pretrained(MODEL_ID)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)

    model.to(device)
    model.eval()

    logger.info(f"Model loaded on {device}")
    yield


app = FastAPI(title="Neural Image Captioner", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class CaptionResult(BaseModel):
    caption: str
    inference_ms: float
    model: str
    device: str
    image_size: list[int]


def generate_caption(image: Image.Image, num_captions: int = 1) -> list[str]:
    """Generate captions for an image."""
    if image.mode != "RGB":
        image = image.convert("RGB")

    pixel_values = feature_extractor(images=[image], return_tensors="pt").pixel_values.to(device)

    kwargs = {
        "max_length": 64,
        "num_beams": 4,
        "num_return_sequences": num_captions,
    }

    with torch.no_grad():
        output_ids = model.generate(pixel_values, **kwargs)

    captions = tokenizer.batch_decode(output_ids, skip_special_tokens=True)
    return [c.strip() for c in captions]


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "model": MODEL_ID,
        "device": str(device),
        "architecture": "ViT (encoder) + GPT-2 (decoder)",
    }


@app.post("/caption", response_model=CaptionResult)
async def caption_image(file: UploadFile = File(...)):
    """Generate a caption for an uploaded image."""
    if model is None:
        raise HTTPException(503, "Model not loaded")

    content = await file.read()
    try:
        image = Image.open(io.BytesIO(content))
    except Exception:
        raise HTTPException(400, "Invalid image file")

    start = time.perf_counter()
    captions = generate_caption(image)
    elapsed = (time.perf_counter() - start) * 1000

    return CaptionResult(
        caption=captions[0],
        inference_ms=round(elapsed, 1),
        model=MODEL_ID,
        device=str(device),
        image_size=list(image.size),
    )


@app.post("/caption/multi")
async def caption_image_multi(file: UploadFile = File(...), num_captions: int = 3):
    """Generate multiple caption candidates for an image."""
    if model is None:
        raise HTTPException(503, "Model not loaded")

    content = await file.read()
    try:
        image = Image.open(io.BytesIO(content))
    except Exception:
        raise HTTPException(400, "Invalid image file")

    start = time.perf_counter()

    if image.mode != "RGB":
        image = image.convert("RGB")

    pixel_values = feature_extractor(images=[image], return_tensors="pt").pixel_values.to(device)

    with torch.no_grad():
        output_ids = model.generate(
            pixel_values,
            max_length=64,
            num_beams=max(num_captions, 4),
            num_return_sequences=min(num_captions, 5),
        )

    captions = tokenizer.batch_decode(output_ids, skip_special_tokens=True)
    captions = [c.strip() for c in captions]

    elapsed = (time.perf_counter() - start) * 1000

    return {
        "captions": captions,
        "count": len(captions),
        "inference_ms": round(elapsed, 1),
        "image_size": list(image.size),
    }


@app.post("/caption/url")
async def caption_from_url(body: dict):
    """Generate a caption from an image URL."""
    import httpx

    url = body.get("url", "")
    if not url:
        raise HTTPException(400, "URL required")

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            image = Image.open(io.BytesIO(resp.content))
    except Exception as e:
        raise HTTPException(400, f"Failed to fetch image: {str(e)}")

    start = time.perf_counter()
    captions = generate_caption(image)
    elapsed = (time.perf_counter() - start) * 1000

    return {
        "caption": captions[0],
        "url": url,
        "inference_ms": round(elapsed, 1),
        "image_size": list(image.size),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8004, reload=True)
