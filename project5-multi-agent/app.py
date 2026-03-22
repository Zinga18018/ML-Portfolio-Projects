"""
Multi-Agent Task Orchestrator
==============================
A framework where multiple specialized AI agents collaborate on tasks.
A planner decomposes work, specialist agents execute subtasks,
and a synthesizer merges results. All powered by TinyLlama via FastAPI.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from enum import Enum
from typing import Optional

import torch
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

MODEL_ID = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
model = None
tokenizer = None
device = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, tokenizer, device
    logger.info(f"Loading {MODEL_ID} for multi-agent system...")
    device = "cuda" if torch.cuda.is_available() else "cpu"

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        device_map="auto" if device == "cuda" else None,
    )
    if device == "cpu":
        model = model.to(device)

    logger.info(f"Model loaded on {device}")
    yield


app = FastAPI(title="Multi-Agent Task Orchestrator", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# -- Agent Definitions --
class AgentRole(str, Enum):
    PLANNER = "planner"
    CODER = "coder"
    RESEARCHER = "researcher"
    ANALYST = "analyst"
    SYNTHESIZER = "synthesizer"


AGENT_PROMPTS = {
    AgentRole.PLANNER: """You are a Planning Agent. Your job is to:
1. Break down the user's task into 2-4 clear subtasks
2. Assign each subtask to the appropriate specialist (coder, researcher, or analyst)
3. Define the order of execution
Output a numbered plan with agent assignments.""",

    AgentRole.CODER: """You are a Code Agent. You write clean, efficient code.
Given a coding subtask, produce the solution with comments.
Focus on correctness and readability.""",

    AgentRole.RESEARCHER: """You are a Research Agent. You analyze topics in depth.
Given a research question, provide a structured analysis with key findings,
evidence, and conclusions.""",

    AgentRole.ANALYST: """You are an Analysis Agent. You examine data and situations.
Given an analysis task, provide quantitative insights, comparisons,
and actionable recommendations.""",

    AgentRole.SYNTHESIZER: """You are a Synthesis Agent. You combine outputs from multiple agents
into a coherent final response. Merge findings, resolve conflicts,
and produce a unified, well-structured answer.""",
}


class TaskRequest(BaseModel):
    task: str
    max_tokens: int = 300
    agents: list[str] = ["planner", "coder", "researcher", "synthesizer"]


class AgentOutput(BaseModel):
    agent: str
    role: str
    output: str
    inference_ms: float


class OrchestrationResult(BaseModel):
    task: str
    plan: str
    agent_outputs: list[AgentOutput]
    final_synthesis: str
    total_time_ms: float
    agents_used: int
    model: str


def run_agent(role: AgentRole, task_context: str, max_tokens: int = 300) -> tuple[str, float]:
    """Run a single agent with the given context."""
    system_prompt = AGENT_PROMPTS[role]
    prompt = f"""<|system|>
{system_prompt}</s>
<|user|>
{task_context}</s>
<|assistant|>
"""
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048).to(device)

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
        )
    elapsed = (time.perf_counter() - start) * 1000

    response_ids = outputs[0][inputs["input_ids"].shape[1]:]
    text = tokenizer.decode(response_ids, skip_special_tokens=True)
    return text.strip(), elapsed


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "model": MODEL_ID,
        "device": str(device),
        "available_agents": [r.value for r in AgentRole],
    }


@app.get("/agents")
async def list_agents():
    """List all available agents and their roles."""
    return {
        "agents": [
            {"role": role.value, "description": prompt.split(".")[0].replace("You are a ", "").strip()}
            for role, prompt in AGENT_PROMPTS.items()
        ]
    }


@app.post("/orchestrate", response_model=OrchestrationResult)
async def orchestrate_task(req: TaskRequest):
    """Run the full multi-agent orchestration pipeline."""
    if model is None:
        raise HTTPException(503, "Model not loaded")

    total_start = time.perf_counter()
    agent_outputs = []

    # Step 1: Planner decomposes the task
    logger.info(f"[Planner] Decomposing task: {req.task[:80]}...")
    plan_text, plan_ms = run_agent(AgentRole.PLANNER, req.task, req.max_tokens)
    agent_outputs.append(AgentOutput(
        agent="planner", role="Task Decomposition",
        output=plan_text, inference_ms=round(plan_ms, 1),
    ))

    # Step 2: Run specialist agents based on requested agents
    specialist_results = []
    for agent_name in req.agents:
        if agent_name in ("planner", "synthesizer"):
            continue

        role = AgentRole(agent_name)
        context = f"Original task: {req.task}\n\nPlan from planner:\n{plan_text}\n\nYour specific assignment: Complete the {agent_name} portion of this plan."

        logger.info(f"[{agent_name.capitalize()}] Executing subtask...")
        output, ms = run_agent(role, context, req.max_tokens)
        agent_outputs.append(AgentOutput(
            agent=agent_name, role=AGENT_PROMPTS[role].split(".")[0].replace("You are a ", "").strip(),
            output=output, inference_ms=round(ms, 1),
        ))
        specialist_results.append(f"[{agent_name.upper()} AGENT OUTPUT]:\n{output}")

    # Step 3: Synthesizer merges all outputs
    synthesis_context = f"""Original task: {req.task}

Plan:
{plan_text}

Agent Results:
{"".join(specialist_results)}

Synthesize all the above into a final, coherent response."""

    logger.info("[Synthesizer] Merging agent outputs...")
    synthesis_text, synth_ms = run_agent(AgentRole.SYNTHESIZER, synthesis_context, req.max_tokens)
    agent_outputs.append(AgentOutput(
        agent="synthesizer", role="Result Synthesis",
        output=synthesis_text, inference_ms=round(synth_ms, 1),
    ))

    total_ms = (time.perf_counter() - total_start) * 1000

    return OrchestrationResult(
        task=req.task,
        plan=plan_text,
        agent_outputs=agent_outputs,
        final_synthesis=synthesis_text,
        total_time_ms=round(total_ms, 1),
        agents_used=len(agent_outputs),
        model=MODEL_ID,
    )


@app.post("/agent/single")
async def run_single_agent(body: dict):
    """Run a single agent without orchestration."""
    if model is None:
        raise HTTPException(503, "Model not loaded")

    role_name = body.get("agent", "researcher")
    task = body.get("task", "")
    max_tokens = body.get("max_tokens", 300)

    if not task:
        raise HTTPException(400, "Task required")

    try:
        role = AgentRole(role_name)
    except ValueError:
        raise HTTPException(400, f"Unknown agent: {role_name}. Available: {[r.value for r in AgentRole]}")

    output, ms = run_agent(role, task, max_tokens)

    return {
        "agent": role_name,
        "task": task[:200],
        "output": output,
        "inference_ms": round(ms, 1),
        "model": MODEL_ID,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8005, reload=True)
