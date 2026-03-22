# Neural Image Captioner

Vision-Language model that generates natural language descriptions of images. Uses a ViT encoder + GPT-2 decoder architecture from HuggingFace.

## Stack
- **Model**: nlpconnect/vit-gpt2-image-captioning (ViT + GPT-2)
- **API**: FastAPI + Uvicorn
- **Image Processing**: Pillow + ViTImageProcessor
- **Inference**: PyTorch with CUDA

## Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/caption` | Caption a single uploaded image |
| POST | `/caption/multi` | Generate multiple caption candidates |
| POST | `/caption/url` | Caption an image from URL |

## Run
```bash
pip install -r requirements.txt
python app.py
# API docs: http://localhost:8004/docs
```

## Example
```bash
curl -X POST http://localhost:8004/caption -F "file=@photo.jpg"
```
