#!/usr/bin/env python3
"""
Nightly VIAM Portal Data Sync
Scrapes clients, distributors, and matching data from https://portal.viam.cx/
Updates data.json (VIAM Portal Mock) and VIAM_DATA in Veracity index.html.

Launches Chrome with Profile 5 (connor@sperocfo.com) via remote debugging,
then connects Playwright to scrape. No cookie export needed.

Usage:
  python sync_viam_data.py              # Run full sync
  python sync_viam_data.py --headed     # Run with visible browser (for debugging)
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
LOG_FILE = SCRIPT_DIR / "sync_log.txt"
VIAM_MOCK_DATA = Path(r"C:\Users\ConnorFinuf\Desktop\Misc Projects\VIAM Portal Mock\data.json")
VERACITY_HTML = Path(r"C:\Users\ConnorFinuf\Desktop\Misc Projects\veracitybusinesssuite\index.html")

CHROME_EXE = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
CHROME_USER_DATA = str(Path(os.environ["LOCALAPPDATA"]) / "Google" / "Chrome" / "User Data")
CHROME_PROFILE = "Profile 5"
DEBUG_PORT = 9222

PORTAL_BASE = "https://portal.viam.cx"
PAGES = {
    "clients": f"{PORTAL_BASE}/clients?searchTerm=&distributors=&statuses=",
    "distributors": f"{PORTAL_BASE}/distributors",
    "matching": f"{PORTAL_BASE}/matching",
}


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def kill_chrome():
    """Kill all Chrome processes."""
    subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"],
                   capture_output=True, text=True)
    time.sleep(2)


def launch_chrome_debug(headed: bool):
    """Launch Chrome with remote debugging enabled."""
    args = [
        CHROME_EXE,
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={CHROME_USER_DATA}",
        f"--profile-directory={CHROME_PROFILE}",
    ]
    if not headed:
        args.append("--headless=new")

    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(5)  # Give Chrome time to start
    return proc


def scrape_table(page, url: str, key: str) -> list[dict]:
    """Navigate to a portal page and scrape the table rows."""
    log(f"Navigating to {key}: {url}")
    page.goto(url, wait_until="networkidle", timeout=60000)

    # Check for login redirect
    if "/login" in page.url or "/auth" in page.url:
        raise RuntimeError(
            f"Redirected to login ({page.url}). "
            "Please log into portal.viam.cx in Chrome (Profile 5) and try again."
        )

    # Wait for table to appear
    page.wait_for_selector("table", timeout=30000)

    # Scroll to load all rows (handle infinite scroll / lazy loading)
    prev_count = 0
    for _ in range(50):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(500)
        rows = page.query_selector_all("table tbody tr")
        if len(rows) == prev_count:
            break
        prev_count = len(rows)

    # Also try clicking "Load More" / "Next" buttons
    for _ in range(100):
        btn = page.query_selector(
            "button:has-text('Load More'), button:has-text('Next'), "
            "button:has-text('Show More'), a:has-text('Next')"
        )
        if not btn or not btn.is_visible():
            break
        btn.click()
        page.wait_for_timeout(1000)

    # Extract headers
    headers = page.eval_on_selector_all(
        "table thead th",
        "els => els.map(el => el.innerText.trim())"
    )

    # Extract rows
    rows_data = page.eval_on_selector_all(
        "table tbody tr",
        "els => els.map(tr => Array.from(tr.querySelectorAll('td')).map(td => td.innerText.trim()))"
    )

    # Build list of dicts
    records = []
    for row in rows_data:
        if len(row) >= len(headers):
            record = {headers[i]: row[i] for i in range(len(headers))}
            records.append(record)
        elif row:
            record = {headers[i]: (row[i] if i < len(row) else "") for i in range(len(headers))}
            records.append(record)

    log(f"  Scraped {len(records)} {key} records ({len(headers)} columns)")
    return records


def run_sync(headed: bool = False):
    """Main sync: launch Chrome with debug port, connect Playwright, scrape, update files."""
    from playwright.sync_api import sync_playwright

    # Kill existing Chrome so we can use the profile
    log("Closing Chrome...")
    kill_chrome()

    # Launch Chrome with remote debugging
    log(f"Launching Chrome ({'headed' if headed else 'headless'}) with Profile 5...")
    chrome_proc = launch_chrome_debug(headed)

    log("Starting VIAM Portal sync...")

    data = {}
    try:
        with sync_playwright() as p:
            # Connect to Chrome via CDP
            browser = p.chromium.connect_over_cdp(f"http://localhost:{DEBUG_PORT}", timeout=30000)
            context = browser.contexts[0]  # Use the existing context (has our profile/cookies)

            # Use existing page or create new one
            if context.pages:
                page = context.pages[0]
            else:
                page = context.new_page()

            for key, url in PAGES.items():
                data[key] = scrape_table(page, url, key)

            browser.close()
    except Exception as e:
        log(f"ERROR: {e}")
        chrome_proc.terminate()
        sys.exit(1)

    chrome_proc.terminate()

    # Validate we got data
    for key in PAGES:
        if not data.get(key):
            log(f"WARNING: No {key} records scraped. Aborting to avoid data loss.")
            sys.exit(1)

    # 1. Update data.json
    log(f"Writing {VIAM_MOCK_DATA}...")
    with open(VIAM_MOCK_DATA, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    log(f"  data.json updated: {len(data['clients'])} clients, "
        f"{len(data['distributors'])} distributors, {len(data['matching'])} matching")

    # 2. Update VIAM_DATA in Veracity index.html
    log(f"Updating VIAM_DATA in {VERACITY_HTML}...")
    html = VERACITY_HTML.read_text(encoding="utf-8")

    pattern = r"(const\s+VIAM_DATA\s*=\s*)(\{[\s\S]*?\})(\s*;)"
    compact_json = json.dumps(data, separators=(",", ":"))
    replacement = f"\\g<1>{compact_json}\\g<3>"

    new_html, count = re.subn(pattern, replacement, html, count=1)
    if count == 0:
        log("ERROR: Could not find VIAM_DATA block in index.html. Manual update needed.")
        sys.exit(1)

    VERACITY_HTML.write_text(new_html, encoding="utf-8")
    log("  Veracity index.html VIAM_DATA updated successfully.")

    log("Sync complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VIAM Portal Data Sync")
    parser.add_argument("--headed", action="store_true", help="Run with visible browser for debugging")
    args = parser.parse_args()

    run_sync(headed=args.headed)
