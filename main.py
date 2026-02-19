"""
main.py
-------
Local entry point — runs the full pipeline on your machine using Chrome.

Usage:
    python main.py
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

import config
from src.scraper    import ElPaisScraper
from src.translator import ArticleTranslator
from src.analyzer   import WordAnalyzer


def build_local_driver() -> webdriver.Chrome:
    """Create a Spanish-locale Chrome driver for local testing."""
    opts = Options()
    opts.page_load_strategy = "eager"          # don't wait for ads/images
    opts.add_argument("--lang=es")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option(
        "prefs", {"intl.accept_languages": "es,es-ES"}
    )
    opts.add_argument(f"--window-size={config.WINDOW_SIZE[0]},{config.WINDOW_SIZE[1]}")
    return webdriver.Chrome(options=opts)


def run_pipeline(driver: webdriver.Chrome, session_label: str = "local") -> list[dict]:
    """
    Scrape → Translate → Analyse.
    Returns list of article dicts with 'title_es' and 'title_en' keys.
    """
    print(f"\n{'='*60}")
    print(f"  Session: {session_label}")
    print(f"{'='*60}")

    # Step 1 — Scrape
    scraper  = ElPaisScraper(driver)
    articles = scraper.scrape()

    # Step 2 — Translate
    translator = ArticleTranslator()
    print("\n  ── Translating titles ──")
    titles_es = [a["title"] for a in articles]
    titles_en = translator.translate_all(titles_es)

    for article, en in zip(articles, titles_en):
        article["title_en"] = en

    # Step 3 — Analyse
    print()
    WordAnalyzer().print_report(titles_en)

    return articles


if __name__ == "__main__":
    driver = build_local_driver()
    try:
        results = run_pipeline(driver, session_label="Chrome (local)")
    finally:
        driver.quit()
