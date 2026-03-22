import io
import time
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from PIL import Image
import torch
from transformers import VisionEncoderDecoderModel, ViTImageProcessor, AutoTokenizer

app = FastAPI()

print("Loading ViT-GPT2...")
model = VisionEncoderDecoderModel.from_pretrained("nlpconnect/vit-gpt2-image-captioning")
processor = ViTImageProcessor.from_pretrained("nlpconnect/vit-gpt2-image-captioning")
tokenizer = AutoTokenizer.from_pretrained("nlpconnect/vit-gpt2-image-captioning")
model.eval()
print("Ready.")

MODE_CONFIG = {
    "quick": {"num_beams": 3, "num_return": 1, "max_length": 32, "temperature": 1.0, "do_sample": False},
    "detailed": {"num_beams": 5, "num_return": 3, "max_length": 64, "temperature": 1.0, "do_sample": False},
    "creative": {"num_beams": 1, "num_return": 3, "max_length": 64, "temperature": 1.2, "do_sample": True},
}


@app.post("/api/caption")
async def caption(file: UploadFile = File(...), mode: str = Form("detailed")):
    content = await file.read()
    image = Image.open(io.BytesIO(content))
    if image.mode != "RGB":
        image = image.convert("RGB")

    pixels = processor(images=[image], return_tensors="pt").pixel_values

    cfg = MODE_CONFIG.get(mode, MODE_CONFIG["detailed"])

    start = time.perf_counter()
    with torch.no_grad():
        gen_kwargs = {
            "max_length": cfg["max_length"],
            "num_beams": cfg["num_beams"],
            "num_return_sequences": cfg["num_return"],
            "use_cache": True,
        }
        if cfg["do_sample"]:
            gen_kwargs["do_sample"] = True
            gen_kwargs["temperature"] = cfg["temperature"]
            gen_kwargs["top_p"] = 0.9

        ids = model.generate(pixels, **gen_kwargs)
    ms = (time.perf_counter() - start) * 1000

    captions = [c.strip() for c in tokenizer.batch_decode(ids, skip_special_tokens=True)]
    # Remove duplicates while preserving order
    seen = set()
    unique = []
    for c in captions:
        if c not in seen:
            seen.add(c)
            unique.append(c)

    w, h = image.size
    return {
        "captions": unique,
        "mode": mode,
        "size": [w, h],
        "ms": round(ms, 1),
        "beams": cfg["num_beams"],
    }


app.mount("/", StaticFiles(directory="static", html=True), name="static")
