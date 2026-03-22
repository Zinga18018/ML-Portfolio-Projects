# Multi-Agent Task Orchestrator

A framework where multiple specialized AI agents collaborate on complex tasks. A planner agent decomposes work, specialist agents (coder, researcher, analyst) execute subtasks, and a synthesizer merges results.

## Stack
- **Model**: TinyLlama/TinyLlama-1.1B-Chat-v1.0
- **Agents**: Planner, Coder, Researcher, Analyst, Synthesizer
- **API**: FastAPI + Uvicorn
- **Orchestration**: Sequential pipeline with Chain-of-Thought

## Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/agents` | List available agents |
| POST | `/orchestrate` | Full multi-agent pipeline |
| POST | `/agent/single` | Run a single agent |

## Run
```bash
pip install -r requirements.txt
python app.py
# API docs: http://localhost:8005/docs
```

## Example
```bash
curl -X POST http://localhost:8005/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"task": "Write a Python function to find prime numbers and analyze its time complexity"}'
```
