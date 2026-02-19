"""
browserstack_runner.py
-----------------------
Runs the El País scraper in PARALLEL across 5 BrowserStack sessions,
covering a mix of desktop and mobile browsers.

Usage:
    python browserstack_runner.py

Credentials are read from environment variables (or a .env file):
    BROWSERSTACK_USERNAME
    BROWSERSTACK_ACCESS_KEY
"""

import os
import time
import threading
from typing import Any

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver

from scraper import run_scraper
from translator import translate_es_to_en
from analyzer import print_analysis, find_repeated_words

load_dotenv()

# ── BrowserStack hub ─────────────────────────────────────────────────────────
BS_USERNAME    = os.getenv("BROWSERSTACK_USERNAME",   "nayanpaleja_TcfLVm")
BS_ACCESS_KEY  = os.getenv("BROWSERSTACK_ACCESS_KEY", "zVftqsPjyf83o9RZ43Gq")
BS_HUB_URL     = f"https://{BS_USERNAME}:{BS_ACCESS_KEY}@hub.browserstack.com/wd/hub"

# ── 5 capability configurations (3 desktop + 2 mobile) ──────────────────────
CAPABILITIES: list[dict[str, Any]] = [
    # 1 — Chrome on Windows 11 (Desktop)
    {
        "bstack:options": {
            "os": "Windows",
            "osVersion": "11",
            "browserVersion": "latest",
            "sessionName": "Chrome Win11",
            "projectName": "ElPais Scraper",
            "buildName": "elpais-opinion-scrape",
        },
        "browserName": "Chrome",
    },
    # 2 — Firefox on Windows 10 (Desktop)
    {
        "bstack:options": {
            "os": "Windows",
            "osVersion": "10",
            "browserVersion": "latest",
            "sessionName": "Firefox Win10",
            "projectName": "ElPais Scraper",
            "buildName": "elpais-opinion-scrape",
        },
        "browserName": "Firefox",
    },
    # 3 — Safari on macOS Ventura (Desktop)
    {
        "bstack:options": {
            "os": "OS X",
            "osVersion": "Ventura",
            "browserVersion": "latest",
            "sessionName": "Safari macOS Ventura",
            "projectName": "ElPais Scraper",
            "buildName": "elpais-opinion-scrape",
        },
        "browserName": "Safari",
    },
    # 4 — Samsung Galaxy S23 / Chrome (Mobile Android)
    {
        "bstack:options": {
            "deviceName": "Samsung Galaxy S23",
            "osVersion": "13.0",
            "sessionName": "Galaxy S23 Chrome",
            "projectName": "ElPais Scraper",
            "buildName": "elpais-opinion-scrape",
            "realMobile": "true",
        },
        "browserName": "Chrome",
    },
    # 5 — iPhone 14 / Safari (Mobile iOS)
    {
        "bstack:options": {
            "deviceName": "iPhone 14",
            "osVersion": "16",
            "sessionName": "iPhone 14 Safari",
            "projectName": "ElPais Scraper",
            "buildName": "elpais-opinion-scrape",
            "realMobile": "true",
        },
        "browserName": "Safari",
    },
]


# ── Per-thread pipeline ──────────────────────────────────────────────────────

def run_pipeline_on_browserstack(
    cap: dict,
    thread_idx: int,
    results: dict,
    lock: threading.Lock,
) -> None:
    """
    Open a BrowserStack remote session, run the full pipeline,
    store results in the shared *results* dict.
    """
    session_name = cap["bstack:options"].get("sessionName", f"Thread-{thread_idx}")
    driver: WebDriver | None = None
    status = "failed"

    print(f"\n[Thread {thread_idx}] Starting: {session_name}")

    try:
        # Build RemoteWebDriver
        driver = webdriver.Remote(
            command_executor=BS_HUB_URL,
            options=_build_options(cap),
        )
        driver.implicitly_wait(10)

        # ── Scrape ──────────────────────────────────────────────────────────
        scrape_result = run_scraper(driver, images_dir=f"images/bs_thread_{thread_idx}")
        articles = scrape_result.get("articles", [])

        # ── Translate ────────────────────────────────────────────────────────
        translated_headers = []
        for art in articles:
            en_title = translate_es_to_en(art["title"])
            art["title_en"] = en_title
            translated_headers.append(en_title)
            time.sleep(0.4)

        # ── Analyse ──────────────────────────────────────────────────────────
        repeated = find_repeated_words(translated_headers, threshold=2)

        # ── Store results ────────────────────────────────────────────────────
        with lock:
            results[thread_idx] = {
                "session": session_name,
                "articles": articles,
                "translated_headers": translated_headers,
                "repeated_words": repeated,
                "status": "passed",
            }

        status = "passed"
        print(f"[Thread {thread_idx}] ✅ PASSED: {session_name}")

    except Exception as exc:
        print(f"[Thread {thread_idx}] ❌ FAILED: {session_name} — {exc}")
        with lock:
            results[thread_idx] = {
                "session": session_name,
                "articles": [],
                "translated_headers": [],
                "repeated_words": {},
                "status": "failed",
            }

    finally:
        if driver:
            try:
                # Mark session pass/fail in BrowserStack dashboard
                reason = "El País Opinion scrape completed" if status == "passed" else "El País Opinion scrape failed"
                script = (
                    '{"action": "setSessionStatus", '
                    f'"arguments": {{"status": "{status}", "reason": "{reason}"}}}}'
                )
                driver.execute_script(f"browserstack_executor: {script}")
            except Exception:
                pass
            driver.quit()


def _build_options(cap: dict):
    """
    Convert a capability dict into the appropriate WebDriver Options object.
    BrowserStack W3C format: capabilities go into the options object directly.
    """
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.firefox.options import Options as FirefoxOptions
    from selenium.webdriver.safari.options import Options as SafariOptions

    browser = cap.get("browserName", "Chrome").lower()

    if browser == "firefox":
        opts = FirefoxOptions()
    elif browser == "safari":
        opts = SafariOptions()
    else:
        opts = ChromeOptions()

    # Eager page load — don't block on slow subresources
    try:
        opts.page_load_strategy = "eager"
    except Exception:
        pass

    # Set Spanish language preference
    opts.add_argument("--lang=es")

    # Merge BrowserStack-specific options
    bs_opts = cap.get("bstack:options", {})
    opts.set_capability("bstack:options", bs_opts)
    opts.set_capability("browserName", cap.get("browserName", "Chrome"))
    if "browserVersion" in bs_opts:
        opts.browser_version = bs_opts["browserVersion"]

    return opts


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 65)
    print("  EL PAÍS OPINION SCRAPER — BrowserStack Parallel Run")
    print(f"  Username : {BS_USERNAME}")
    print(f"  Threads  : {len(CAPABILITIES)}")
    print("=" * 65)

    results: dict = {}
    lock = threading.Lock()
    threads: list[threading.Thread] = []

    for idx, cap in enumerate(CAPABILITIES, start=1):
        t = threading.Thread(
            target=run_pipeline_on_browserstack,
            args=(cap, idx, results, lock),
            daemon=True,
        )
        threads.append(t)

    # Start all threads simultaneously
    for t in threads:
        t.start()
        time.sleep(0.5)   # small stagger to avoid race on BrowserStack init

    # Wait for all threads to finish (with a 10 minute safety timeout each)
    for t in threads:
        t.join(timeout=600)

    # ── Consolidated report ──────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("  CONSOLIDATED RESULTS")
    print("=" * 65)

    all_translated_headers: list[str] = []

    for idx in sorted(results.keys()):
        r = results[idx]
        print(f"\n{'─'*65}")
        print(f"  Thread {idx}: {r['session']}  [{r['status'].upper()}]")
        print(f"{'─'*65}")
        for i, art in enumerate(r["articles"], start=1):
            print(f"  [{i}] ES: {art['title']}")
            print(f"       EN: {art.get('title_en', '')}")
            print(f"       Image: {art.get('image') or 'N/A'}")
        all_translated_headers.extend(r["translated_headers"])

    # Global word analysis across all sessions
    print_analysis(all_translated_headers, threshold=2)

    # Summary table
    print("=" * 65)
    print("  SESSION STATUS SUMMARY")
    print("=" * 65)
    print(f"  {'#':<5} {'Session':<35} {'Status'}")
    print(f"  {'-'*5} {'-'*35} {'-'*8}")
    for idx in sorted(results.keys()):
        r = results[idx]
        icon = "✅" if r["status"] == "passed" else "❌"
        print(f"  {idx:<5} {r['session']:<35} {icon} {r['status'].upper()}")
    print()


if __name__ == "__main__":
    main()
