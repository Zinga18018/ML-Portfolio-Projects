"""Wake up sleeping HF Spaces and take screenshots once loaded."""
from playwright.sync_api import sync_playwright
import time
import os

# Only retake the 4 that were sleeping
SPACES = [
    ("rag-document-brain", "https://yogesh18018-rag-document-brain.hf.space"),
    ("sentiment-engine", "https://yogesh18018-sentiment-engine.hf.space"),
    ("image-captioner", "https://yogesh18018-image-captioner.hf.space"),
    ("multi-agent", "https://yogesh18018-multi-agent.hf.space"),
]

OUT_DIR = os.path.join(os.path.dirname(__file__), "portfolio-website", "screenshots")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    # Step 1: Open all spaces in parallel tabs to wake them up
    pages = []
    for name, url in SPACES:
        print(f"[*] Waking up {name}...")
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(url, timeout=120000, wait_until="commit")
        pages.append((name, url, page))

    # Step 2: Wait for all to load (check every 10s for up to 5 min)
    print("\n[*] Waiting for all spaces to finish booting...")
    max_wait = 300  # 5 minutes max
    check_interval = 15
    elapsed = 0

    while elapsed < max_wait:
        time.sleep(check_interval)
        elapsed += check_interval
        print(f"    {elapsed}s elapsed...")

        all_ready = True
        for name, url, page in pages:
            content = page.content()
            if "Preparing Space" in content or "is currently building" in content:
                all_ready = False
                print(f"    {name}: still loading...")
            else:
                print(f"    {name}: READY")

        if all_ready:
            print("\n[+] All spaces are ready!")
            break
    else:
        print("\n[!] Timeout reached, taking screenshots anyway")

    # Step 3: Reload each page and take screenshot
    for name, url, page in pages:
        print(f"\n[*] Capturing {name}...")
        try:
            page.reload(timeout=60000, wait_until="networkidle")
            time.sleep(3)
        except:
            pass
        out_path = os.path.join(OUT_DIR, f"{name}.png")
        page.screenshot(path=out_path, clip={"x": 0, "y": 0, "width": 1280, "height": 800})
        print(f"    Saved: {out_path}")
        page.close()

    browser.close()
    print("\n[+] Done!")
