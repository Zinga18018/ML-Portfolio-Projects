"""
Multi-Agent Task Orchestrator -- Hugging Face Spaces (Docker)
TinyLlama-1.1B multi-agent system with KV cache optimization.
"""

import time
import torch
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer

app = FastAPI()

MODEL_ID = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

print(f"Loading {MODEL_ID}...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
model = AutoModelForCausalLM.from_pretrained(MODEL_ID, torch_dtype=torch.float32)
model.eval()
print("Model loaded on CPU with KV cache enabled.")

AGENT_PROMPTS = {
    "planner": (
        "You are a Planning Agent. Break down the user's task into 2-4 clear subtasks. "
        "Assign each subtask to the appropriate specialist (coder, researcher, or analyst). "
        "Output a numbered plan with agent assignments."
    ),
    "coder": (
        "You are a Code Agent. You write clean, efficient code. "
        "Given a coding subtask, produce the solution with comments. "
        "Focus on correctness and readability."
    ),
    "researcher": (
        "You are a Research Agent. You analyze topics in depth. "
        "Given a research question, provide a structured analysis with key findings, "
        "evidence, and conclusions."
    ),
    "analyst": (
        "You are an Analysis Agent. You examine data and situations. "
        "Given an analysis task, provide quantitative insights, comparisons, "
        "and actionable recommendations."
    ),
    "synthesizer": (
        "You are a Synthesis Agent. You combine outputs from multiple agents "
        "into a coherent final response. Merge findings, resolve conflicts, "
        "and produce a unified, well-structured answer."
    ),
}


def run_agent(role, context, max_tokens=300):
    prompt = (
        f"<|system|>\n{AGENT_PROMPTS[role]}</s>\n"
        f"<|user|>\n{context}</s>\n"
        f"<|assistant|>\n"
    )
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048)

    start = time.perf_counter()
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=0.7,
            top_p=0.9,
            do_sample=True,
            repetition_penalty=1.15,
            pad_token_id=tokenizer.eos_token_id,
            use_cache=True,
        )
    elapsed = (time.perf_counter() - start) * 1000

    response_ids = outputs[0][inputs["input_ids"].shape[1]:]
    text = tokenizer.decode(response_ids, skip_special_tokens=True).strip()
    toks = len(response_ids)
    return text, elapsed, toks


class OrchestrateRequest(BaseModel):
    task: str
    agents: list[str] = ["coder", "researcher"]
    max_tokens: int = 300


class SingleRequest(BaseModel):
    agent: str
    task: str
    max_tokens: int = 300


@app.post("/api/orchestrate")
def orchestrate(req: OrchestrateRequest):
    if not req.task.strip():
        return {"error": "Empty task."}

    total_start = time.perf_counter()
    phases = []

    # Phase 1: Planner
    plan_text, plan_ms, plan_toks = run_agent("planner", req.task, req.max_tokens)
    phases.append({"agent": "planner", "label": "Decomposing task", "output": plan_text, "ms": round(plan_ms, 1), "tokens": plan_toks})

    # Phase 2: Specialists
    specialist_outputs = []
    for agent in req.agents:
        if agent not in AGENT_PROMPTS or agent in ("planner", "synthesizer"):
            continue
        context = (
            f"Original task: {req.task}\n\n"
            f"Plan from planner:\n{plan_text}\n\n"
            f"Your assignment: Complete the {agent} portion of this plan."
        )
        text, ms, toks = run_agent(agent, context, req.max_tokens)
        phases.append({"agent": agent, "label": "Executing", "output": text, "ms": round(ms, 1), "tokens": toks})
        specialist_outputs.append(f"[{agent.upper()}]: {text}")

    # Phase 3: Synthesizer
    synth_context = (
        f"Original task: {req.task}\n\n"
        f"Plan:\n{plan_text}\n\n"
        f"Agent Results:\n" + "\n\n".join(specialist_outputs) +
        "\n\nSynthesize into a final response."
    )
    synth_text, synth_ms, synth_toks = run_agent("synthesizer", synth_context, req.max_tokens)
    phases.append({"agent": "synthesizer", "label": "Merging results", "output": synth_text, "ms": round(synth_ms, 1), "tokens": synth_toks})

    total_ms = (time.perf_counter() - total_start) * 1000
    return {"phases": phases, "total_ms": round(total_ms, 1), "agent_count": len(phases)}


@app.post("/api/single")
def run_single(req: SingleRequest):
    if not req.task.strip():
        return {"error": "Empty task."}
    agent = req.agent.lower()
    if agent not in AGENT_PROMPTS:
        return {"error": f"Unknown agent: {agent}"}

    text, ms, toks = run_agent(agent, req.task, req.max_tokens)
    return {"agent": agent, "output": text, "ms": round(ms, 1), "tokens": toks}


app.mount("/", StaticFiles(directory="static", html=True), name="static")
