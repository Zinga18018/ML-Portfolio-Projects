"""
Master Launcher - Start all AI project servers
================================================
Launches all 5 FastAPI servers + portfolio website.
"""

import subprocess
import sys
import os
import time
import signal

PYTHON = sys.executable
BASE = os.path.dirname(os.path.abspath(__file__))

SERVERS = [
    {"name": "Portfolio Website", "cmd": [PYTHON, "-m", "http.server", "8080", "--directory", os.path.join(BASE, "portfolio-website")], "port": 8080},
    {"name": "AI Code Reviewer", "cmd": [PYTHON, "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"], "port": 8001, "cwd": os.path.join(BASE, "project1-ai-code-reviewer")},
    {"name": "RAG Document Brain", "cmd": [PYTHON, "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8002"], "port": 8002, "cwd": os.path.join(BASE, "project2-rag-document-brain")},
    {"name": "Sentiment Engine", "cmd": [PYTHON, "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8003"], "port": 8003, "cwd": os.path.join(BASE, "project3-sentiment-engine")},
    {"name": "Image Captioner", "cmd": [PYTHON, "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8004"], "port": 8004, "cwd": os.path.join(BASE, "project4-image-captioner")},
    {"name": "Multi-Agent Orchestrator", "cmd": [PYTHON, "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8005"], "port": 8005, "cwd": os.path.join(BASE, "project5-multi-agent")},
]


def main():
    print("=" * 60)
    print("  AI PORTFOLIO - MASTER LAUNCHER")
    print("=" * 60)
    print()

    processes = []

    for server in SERVERS:
        cwd = server.get("cwd", BASE)
        print(f"  Starting {server['name']} on port {server['port']}...")
        proc = subprocess.Popen(
            server["cmd"],
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        processes.append((server["name"], proc, server["port"]))

    print()
    print("-" * 60)
    print("  All servers launched:")
    print()
    for name, proc, port in processes:
        print(f"    {name:30s} -> http://localhost:{port}")
    print()
    print("  Portfolio:  http://localhost:8080")
    print("  API Docs:   http://localhost:800X/docs")
    print()
    print("  Press Ctrl+C to stop all servers")
    print("-" * 60)

    try:
        while True:
            time.sleep(1)
            # Check if any died
            for name, proc, port in processes:
                if proc.poll() is not None:
                    print(f"  [!] {name} exited with code {proc.returncode}")
    except KeyboardInterrupt:
        print("\n  Shutting down all servers...")
        for name, proc, port in processes:
            proc.terminate()
        for name, proc, port in processes:
            proc.wait(timeout=5)
        print("  All servers stopped.")


if __name__ == "__main__":
    main()
