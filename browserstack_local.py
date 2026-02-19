"""
browserstack_local.py
---------------------
Local entry point — runs the full pipeline sequentially using a local
Chrome WebDriver. No BrowserStack account required.

Pipeline:
  1. Scrape El País Opinion (scraper.py)
  2. Translate titles ES → EN (translator.py)
  3. Analyse word frequency in translated headers (analyzer.py)
"""

import os
import time
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from scraper import run_scraper
from translator import translate_es_to_en
from analyzer import print_analysis

load_dotenv()


def build_local_driver() -> webdriver.Chrome:
    """Return a Spanish-locale Chrome driver."""
    opts = Options()
    opts.add_argument("--lang=es")
    opts.add_argument("--accept-lang=es-ES,es")
    opts.add_experimental_option("prefs", {
        "intl.accept_languages": "es,es-ES",
    })
    opts.page_load_strategy = "eager"   # don't wait for all sub-resources
    # Uncomment the next line to run headless (no visible browser window):
    # opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1280,900")
    return webdriver.Chrome(options=opts)


def run_pipeline(driver, label: str = "LOCAL") -> None:
    print(f"\n{'='*65}")
    print(f"  PIPELINE START  [{label}]")
    print(f"{'='*65}")

    # ── Step 1: Scrape ───────────────────────────────────────────────────────
    result = run_scraper(driver)
    articles = result.get("articles", [])

    if not articles:
        print("\n  [pipeline] No articles scraped — aborting pipeline.\n")
        return

    # ── Step 2: Translate headers ────────────────────────────────────────────
    print("\n── Translating article titles (ES → EN) ────────────────────────")
    translated_headers = []
    for i, art in enumerate(articles, start=1):
        spanish_title = art["title"]
        print(f"  Translating [{i}]: {spanish_title}")
        english_title = translate_es_to_en(spanish_title)
        art["title_en"] = english_title
        translated_headers.append(english_title)
        print(f"       → EN  : {english_title}\n")
        time.sleep(0.5)  # be polite to the free API

    # ── Step 3: Print summary table ──────────────────────────────────────────
    print("\n" + "=" * 65)
    print("  ARTICLE SUMMARY")
    print("=" * 65)
    for i, art in enumerate(articles, start=1):
        print(f"\n  [{i}] {art['title']}")
        print(f"       EN: {art.get('title_en', '')}")
        print(f"       Image: {art.get('image') or 'N/A'}")
        print(f"       URL: {art['url']}")

    # ── Step 4: Word-frequency analysis ─────────────────────────────────────
    print_analysis(translated_headers, threshold=2)

    print(f"{'='*65}")
    print(f"  PIPELINE COMPLETE  [{label}]")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    driver = build_local_driver()
    driver.maximize_window()
    try:
        run_pipeline(driver, label="LOCAL — Chrome")
    finally:
        driver.quit()
