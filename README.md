# AI Portfolio Projects

Five FastAPI examples using pretrained models, alongside separate Hugging Face Space variants and a static portfolio website. The code supports experimentation with model serving; this repository does not establish production readiness or measured GPU performance.

## API variants in this repository

| Project directory | Model | Port | Implemented behavior |
|---|---|---|---|
| [project1-ai-code-reviewer](project1-ai-code-reviewer) | TinyLlama-1.1B | 8001 | Free-text code suggestions and SSE streaming |
| [project2-rag-document-brain](project2-rag-document-brain) | all-MiniLM-L6-v2 | 8002 | Chroma passage retrieval and formatted source previews |
| [project3-sentiment-engine](project3-sentiment-engine) | DistilBERT SST-2 | 8003 | Binary sentiment, batches and summaries |
| [project4-image-captioner](project4-image-captioner) | ViT-GPT2 | 8004 | Image captions and beam alternatives |
| [project5-multi-agent](project5-multi-agent) | TinyLlama-1.1B | 8005 | Sequential prompt roles and synthesis |

Model identifiers used by the source are `TinyLlama/TinyLlama-1.1B-Chat-v1.0`, `all-MiniLM-L6-v2`, `distilbert-base-uncased-finetuned-sst-2-english` and `nlpconnect/vit-gpt2-image-captioning`. These are pretrained models, not models trained in this repository.

## Run one API locally

Use Python 3.10+ and install the chosen project's requirements, not an assumed root requirements file. For example:

```bash
git clone https://github.com/Zinga18018/ML-Portfolio-Projects.git
cd ML-Portfolio-Projects
python -m venv .venv
source .venv/bin/activate
python -m pip install -r project3-sentiment-engine/requirements.txt
cd project3-sentiment-engine
uvicorn app:app --host 127.0.0.1 --port 8003
```

On Windows PowerShell, use `.\.venv\Scripts\Activate.ps1` for activation before entering the project directory. Open `http://127.0.0.1:8003/docs`. Other API folders use the same entry-point name with their listed ports.

Models load on startup or import and download if uncached. The API code selects CUDA when available and otherwise CPU; an NVIDIA GPU is not mandatory. Dependency lists specify minimum versions, not a tested lockfile. Disk, memory and startup time depend on the selected models and environment.

The [explicit Uvicorn host](https://uvicorn.dev/settings/) keeps this command on loopback. Each project's `python app.py` entry point instead binds all interfaces with reload enabled.

## Launcher and website

From the repository root, `python launch_all.py` spawns all five APIs plus the website, using the launcher's Python interpreter. [launch_all.py](launch_all.py) does not install dependencies or wait for model-ready health checks; starting processes is not proof that the services are ready. It binds API servers to all interfaces and can load multiple model copies. Prefer one loopback API for initial local use.

To serve only the static site from the repository root with [Python's HTTP server](https://docs.python.org/3/library/http.server.html):

```bash
python -m http.server 8080 --bind 127.0.0.1 --directory portfolio-website
```

This serves [portfolio-website](portfolio-website), not model backends. The [Pages workflow](.github/workflows/deploy-pages.yml) publishes these static files; it is not backend deployment or runtime testing.

## Related implementations are not interchangeable

[hf-spaces](hf-spaces) contains separate CPU-oriented Docker applications with different routes, commonly prefixed `/api`, served on port 7860. For example, its RAG variant adds TinyLlama answers and PDF/CSV handling, its reviewer parses severity labels, and its sentiment app adds a keyword-based emotion overlay. The project-directory RAG API above only formats retrieved passages and decodes uploaded bytes; it does not parse PDFs or generate answers.

Related modular repositories are [ai-code-reviewer](https://github.com/Zinga18018/ai-code-reviewer), [rag-document-brain](https://github.com/Zinga18018/rag-document-brain), [sentiment-engine](https://github.com/Zinga18018/sentiment-engine), [image-captioner](https://github.com/Zinga18018/image-captioner) and [multi-agent-orchestrator](https://github.com/Zinga18018/multi-agent-orchestrator). Shared project/model identity does not make their code, UI features or screenshots equivalent.

## Limits and verification

These APIs have no authentication and permissive CORS. Image URL fetching and upload handling also need hardening before untrusted access. Generated reviews, captions and role outputs can be wrong; retrieval similarity and classifier scores are not correctness guarantees.

No automated model evaluation, runtime test suite or hardware benchmark is committed. Setup, model execution, deployment status and browser flows were not rerun for this documentation update. Existing portfolio assets and runtime files are unchanged.

