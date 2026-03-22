# AI Portfolio Projects

5 production-deployed AI projects powered by real transformer models. TinyLlama, DistilBERT, ViT-GPT2, Sentence-Transformers -- all running on PyTorch with CUDA acceleration.

## Projects

| # | Project | Model | Port | Description |
|---|---------|-------|------|-------------|
| 1 | **AI Code Reviewer** | TinyLlama-1.1B | 8001 | LLM-powered code reviews with streaming |
| 2 | **RAG Document Brain** | all-MiniLM-L6-v2 | 8002 | Semantic search + document Q&A via ChromaDB |
| 3 | **Sentiment Engine** | DistilBERT | 8003 | Real-time sentiment analysis with batch support |
| 4 | **Image Captioner** | ViT + GPT-2 | 8004 | Vision-language image captioning |
| 5 | **Multi-Agent Orchestrator** | TinyLlama-1.1B | 8005 | Multi-agent task decomposition + synthesis |

## Quick Start

```bash
# Run a single project
cd project3-sentiment-engine
pip install -r requirements.txt
python app.py
# Open http://localhost:8003/docs

# Or run everything
python launch_all.py
```

## Portfolio Website
```bash
# Constellation-themed portfolio on port 8080
python -m http.server 8080 --directory portfolio-website
```

## Requirements
- Python 3.10+
- PyTorch with CUDA
- NVIDIA GPU (tested on RTX 4060)
- ~8GB disk for model weights (cached by HuggingFace)
