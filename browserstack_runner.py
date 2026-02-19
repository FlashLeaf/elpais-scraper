"""
browserstack_runner.py
----------------------
Runs the El País scraper in PARALLEL across 5 browser/device combinations
on BrowserStack Automate.

Usage:
    python browserstack_runner.py
"""

import threading
from selenium import webdriver
from selenium.webdriver.chrome.options  import Options  as ChromeOptions
from selenium.webdriver.firefox.options import Options  as FirefoxOptions

import config
from main import run_pipeline


# ── Driver factory ────────────────────────────────────────────────────────────

def build_bs_driver(caps: dict) -> webdriver.Remote:
    """Build a BrowserStack Remote WebDriver from a capability dict."""
    browser = caps.get("browserName", "Chrome").lower()

    if browser == "firefox":
        opts = FirefoxOptions()
    else:
        opts = ChromeOptions()

    for key, value in caps.items():
        opts.set_capability(key, value)

    return webdriver.Remote(
        command_executor=config.BS_HUB_URL,
        options=opts
    )


# ── Per-thread task ───────────────────────────────────────────────────────────

def run_session(caps: dict, thread_num: int, results: dict) -> None:
    """Run the full pipeline on a single BrowserStack session."""
    session_label = caps["bstack:options"]["sessionName"]
    status  = "failed"
    driver  = None
    try:
        print(f"\n[Thread {thread_num}] Starting: {session_label}")
        driver  = build_bs_driver(caps)
        articles = run_pipeline(driver, session_label=session_label)
        status  = "passed"
        results[thread_num] = {
            "label":    session_label,
            "status":   status,
            "articles": articles,
        }

    except Exception as exc:
        print(f"[Thread {thread_num}] ERROR: {exc}")
        results[thread_num] = {"label": session_label, "status": "failed", "articles": []}

    finally:
        if driver:
            try:
                # Mark session in BrowserStack dashboard
                reason = "Scrape complete" if status == "passed" else "Scrape failed"
                script = (
                    '{"action":"setSessionStatus",'
                    f'"arguments":{{"status":"{status}","reason":"{reason}"}}}}'
                )
                driver.execute_script(f"browserstack_executor: {script}")
            except Exception:
                pass
            driver.quit()

    print(f"[Thread {thread_num}] {'✅ PASSED' if status=='passed' else '❌ FAILED'}: {session_label}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    print("="*65)
    print("  EL PAÍS OPINION SCRAPER — BrowserStack Parallel Run")
    print(f"  Username : {config.BS_USERNAME}")
    print(f"  Sessions : {len(config.BS_CAPABILITIES)}")
    print("="*65)

    results: dict = {}
    threads = []

    for i, caps in enumerate(config.BS_CAPABILITIES, start=1):
        t = threading.Thread(
            target=run_session,
            args=(caps, i, results),
            daemon=True,
        )
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=600)   # max 10 min per thread

    # ── Consolidated report ───────────────────────────────────────────────────
    print("\n" + "="*65)
    print("  RESULTS")
    print("="*65)

    all_titles_en = []

    for idx in sorted(results):
        r = results[idx]
        status_icon = "✅" if r["status"] == "passed" else "❌"
        print(f"\n  {status_icon} Thread {idx}: {r['label']} [{r['status'].upper()}]")
        print("  " + "-"*60)
        for j, art in enumerate(r.get("articles", []), start=1):
            print(f"    [{j}] ES: {art.get('title','—')}")
            print(f"         EN: {art.get('title_en','—')}")
            print(f"         🖼  {art.get('image','(no image)')}")
            if art.get("title_en"):
                all_titles_en.append(art["title_en"])

    # Global word-frequency analysis across all sessions
    from src.analyzer import WordAnalyzer
    print("\n" + "="*65)
    print("  WORD FREQUENCY (all sessions combined)")
    print("="*65)
    WordAnalyzer().print_report(all_titles_en)

    # Session summary table
    print("="*65)
    print("  SESSION SUMMARY")
    print("="*65)
    print(f"  {'#':<3} {'Session':<35} {'Status'}")
    print(f"  {'-'*3} {'-'*35} {'-'*8}")
    for idx in sorted(results):
        r = results[idx]
        icon = "✅ PASSED" if r["status"] == "passed" else "❌ FAILED"
        print(f"  {idx:<3} {r['label']:<35} {icon}")
    print("="*65)


if __name__ == "__main__":
    main()
