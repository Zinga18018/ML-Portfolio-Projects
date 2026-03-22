"""Take screenshots of all 5 HF Spaces for portfolio."""
from playwright.sync_api import sync_playwright
import time
import os

SPACES = [
    ("ai-code-reviewer", "https://yogesh18018-ai-code-reviewer.hf.space"),
    ("rag-document-brain", "https://yogesh18018-rag-document-brain.hf.space"),
    ("sentiment-engine", "https://yogesh18018-sentiment-engine.hf.space"),
    ("image-captioner", "https://yogesh18018-image-captioner.hf.space"),
    ("multi-agent", "https://yogesh18018-multi-agent.hf.space"),
]

OUT_DIR = os.path.join(os.path.dirname(__file__), "portfolio-website", "screenshots")
os.makedirs(OUT_DIR, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    for name, url in SPACES:
        print(f"[*] Capturing {name}...")
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        try:
            page.goto(url, timeout=90000, wait_until="networkidle")
            # Extra wait for JS rendering
            time.sleep(3)
            out_path = os.path.join(OUT_DIR, f"{name}.png")
            page.screenshot(path=out_path, clip={"x": 0, "y": 0, "width": 1280, "height": 800})
            print(f"    Saved: {out_path}")
        except Exception as e:
            print(f"    Error on {name}: {e}")
            # Take screenshot anyway even if timeout
            try:
                out_path = os.path.join(OUT_DIR, f"{name}.png")
                page.screenshot(path=out_path, clip={"x": 0, "y": 0, "width": 1280, "height": 800})
                print(f"    Saved fallback screenshot: {out_path}")
            except:
                print(f"    Could not save screenshot for {name}")
        finally:
            page.close()

    browser.close()
    print("\n[+] All screenshots complete!")
