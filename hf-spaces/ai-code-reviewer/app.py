import time
import re
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

app = FastAPI()

print("Loading TinyLlama...")
tokenizer = AutoTokenizer.from_pretrained("TinyLlama/TinyLlama-1.1B-Chat-v1.0")
model = AutoModelForCausalLM.from_pretrained("TinyLlama/TinyLlama-1.1B-Chat-v1.0", torch_dtype=torch.float32)
model.eval()
print("Ready.")

SYSTEM = (
    "You are an expert code reviewer. Analyze the code and provide a structured review.\n"
    "For each issue found, output it on its own line in this format:\n"
    "[SEVERITY:CATEGORY] Description of the issue\n"
    "Where SEVERITY is CRITICAL, WARNING, or INFO\n"
    "Where CATEGORY is BUG, SECURITY, PERFORMANCE, or STYLE\n\n"
    "After listing issues, end with a final line:\n"
    "VERDICT: APPROVE or REQUEST_CHANGES or NEEDS_DISCUSSION\n"
    "SCORE: X/100\n"
    "Be specific. Reference line numbers when possible."
)

FOCUS_MAP = {
    "general": "Review all aspects.",
    "security": "Focus on security vulnerabilities.",
    "performance": "Focus on performance bottlenecks.",
    "style": "Focus on code style and readability.",
}


class ReviewRequest(BaseModel):
    code: str
    language: str = "python"
    focus: str = "general"
    max_tokens: int = 384


@app.post("/api/review")
def review(req: ReviewRequest):
    focus_text = FOCUS_MAP.get(req.focus, FOCUS_MAP["general"])
    prompt = f"<|system|>\n{SYSTEM}\n{focus_text}</s>\n<|user|>\nReview this {req.language} code:\n\n```{req.language}\n{req.code}\n```</s>\n<|assistant|>\n"

    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048)

    start = time.perf_counter()
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=req.max_tokens, temperature=0.7,
                             top_p=0.9, do_sample=True, repetition_penalty=1.1,
                             pad_token_id=tokenizer.eos_token_id, use_cache=True)
    ms = (time.perf_counter() - start) * 1000

    new_ids = out[0][inputs["input_ids"].shape[1]:]
    text = tokenizer.decode(new_ids, skip_special_tokens=True).strip()
    toks = len(new_ids)
    tps = toks / (ms / 1000) if ms > 0 else 0

    # Parse structured issues from output
    issues = []
    lines = text.split('\n')
    verdict = "NEEDS_DISCUSSION"
    score = 65

    for line in lines:
        line = line.strip()
        # Match [SEVERITY:CATEGORY] pattern
        m = re.match(r'\[(\w+):(\w+)\]\s*(.*)', line)
        if m:
            issues.append({
                "severity": m.group(1).upper(),
                "category": m.group(2).upper(),
                "message": m.group(3).strip(),
            })
        # Match VERDICT
        vm = re.match(r'VERDICT:\s*(\w+)', line, re.IGNORECASE)
        if vm:
            verdict = vm.group(1).upper()
        # Match SCORE
        sm = re.match(r'SCORE:\s*(\d+)', line, re.IGNORECASE)
        if sm:
            score = min(int(sm.group(1)), 100)

    # Fallback: if no structured issues parsed, create one from raw text
    if not issues and text.strip():
        issues.append({
            "severity": "INFO",
            "category": "GENERAL",
            "message": text[:500],
        })

    # Compute category counts
    counts = {"BUG": 0, "SECURITY": 0, "PERFORMANCE": 0, "STYLE": 0, "GENERAL": 0}
    severity_counts = {"CRITICAL": 0, "WARNING": 0, "INFO": 0}
    for iss in issues:
        cat = iss["category"]
        sev = iss["severity"]
        if cat in counts:
            counts[cat] += 1
        if sev in severity_counts:
            severity_counts[sev] += 1

    # Auto-adjust score based on issues if model didn't provide one
    if not any(re.match(r'SCORE:', l, re.IGNORECASE) for l in lines):
        score = max(0, 100 - severity_counts["CRITICAL"] * 25 - severity_counts["WARNING"] * 10 - severity_counts["INFO"] * 3)

    return {
        "raw": text,
        "issues": issues,
        "verdict": verdict,
        "score": score,
        "counts": counts,
        "severity_counts": severity_counts,
        "tokens": toks,
        "ms": round(ms, 1),
        "tps": round(tps, 1),
    }


app.mount("/", StaticFiles(directory="static", html=True), name="static")
