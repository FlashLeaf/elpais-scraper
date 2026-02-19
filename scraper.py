"""
scraper.py
----------
Core El País Opinion-section scraper.

Accepts a pre-configured Selenium WebDriver instance so it can be
used both locally (Chrome) and remotely (BrowserStack Remote).

Public API
----------
run_scraper(driver, images_dir="images") -> dict
    Runs the full scrape on the given driver.
    Returns:
        {
            "articles": [
                {
                    "title":   str,   # Spanish title
                    "content": str,   # Spanish body text (first ~500 chars)
                    "image":   str | None,  # Local path to downloaded image, or None
                    "url":     str,   # Article URL
                }
            ]
        }
"""

import os
import re
import time
import random
import requests

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
)

OPINION_URL = "https://elpais.com/opinion/"
MAX_ARTICLES = 5
WAIT_TIMEOUT = 15      # seconds
IMAGE_DIR = "images"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _safe_find(driver, by, value, timeout=WAIT_TIMEOUT):
    """Wait for a single element, return None on timeout."""
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
    except (TimeoutException, NoSuchElementException):
        return None


def _safe_find_all(driver, by, value, timeout=WAIT_TIMEOUT):
    """Wait for ≥1 elements, return empty list on timeout."""
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        return driver.find_elements(by, value)
    except TimeoutException:
        return []


def _dismiss_consent(driver):
    """
    Try to click the cookie / GDPR consent button.
    El País uses a CMP overlay; several selectors are tried in order.
    """
    consent_selectors = [
        (By.ID, "didomi-notice-agree-button"),
        (By.XPATH, "//button[contains(translate(text(),'ACEPTAR','aceptar'),'aceptar')]"),
        (By.XPATH, "//button[contains(@class,'accept')]"),
        (By.XPATH, "//button[contains(text(),'Accept')]"),
        (By.CSS_SELECTOR, "button.css-1ynyhfy"),       # observed class 2024-25
        (By.CSS_SELECTOR, "[data-testid='accept-button']"),
    ]
    for by, value in consent_selectors:
        try:
            btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((by, value))
            )
            btn.click()
            time.sleep(1.5)
            print("  [scraper] Consent banner dismissed.")
            return
        except (TimeoutException, NoSuchElementException, WebDriverException):
            continue
    print("  [scraper] No consent banner found (or already dismissed).")


def _is_article_url(href: str) -> bool:
    """
    Return True only for real article URLs (contain a date segment like /2026-02-19/).
    Filters out section-index pages like /opinion/editoriales/ or /opinion/tribunas/.
    """
    if not href or "elpais.com" not in href:
        return False
    if "/opinion/" not in href:
        return False
    # Must have a year-month-day slug anywhere in the path
    if not re.search(r"/\d{4}-\d{2}-\d{2}/", href):
        return False
    # Exclude the bare opinion root
    if href.rstrip("/").endswith("/opinion"):
        return False
    return True


def _extract_article_urls(driver) -> list[str]:
    """
    Collect the first MAX_ARTICLES dated article URLs from the Opinion listing page.
    Only real article URLs (containing a YYYY-MM-DD date segment) are returned.
    Multiple CSS selector strategies are attempted for robustness.
    """
    # Step 1: try article-card selectors first
    selectors = [
        "article.c a[href]",
        "article h2 a",
        "h2.c_t a",
        "div.c_d h2 a",
        "div.c_h a",
        "article a[href]",
    ]
    seen: set = set()
    hrefs: list = []

    for selector in selectors:
        elements = driver.find_elements(By.CSS_SELECTOR, selector)
        for el in elements:
            href = el.get_attribute("href") or ""
            if _is_article_url(href) and href not in seen:
                seen.add(href)
                hrefs.append(href)
            if len(hrefs) >= MAX_ARTICLES:
                return hrefs
        if hrefs:
            # Got some — keep looking only if we need more
            pass

    if len(hrefs) >= MAX_ARTICLES:
        return hrefs

    # Step 2: last-resort — scan ALL links on the page
    all_links = driver.find_elements(By.TAG_NAME, "a")
    for el in all_links:
        href = el.get_attribute("href") or ""
        if _is_article_url(href) and href not in seen:
            seen.add(href)
            hrefs.append(href)
        if len(hrefs) >= MAX_ARTICLES:
            break

    return hrefs


def _extract_title(driver) -> str:
    """Extract article title (h1 → og:title → page title)."""
    for selector in ["h1.a_t", "h1.article-title", "h1"]:
        el = _safe_find(driver, By.CSS_SELECTOR, selector, timeout=6)
        if el and el.text.strip():
            return el.text.strip()
    # og:title fallback
    try:
        meta = driver.find_element(By.XPATH, "//meta[@property='og:title']")
        return meta.get_attribute("content").strip()
    except NoSuchElementException:
        pass
    return driver.title.strip()


def _extract_content(driver) -> str:
    """Extract article body text (first ~600 chars)."""
    body_selectors = [
        "div.a_b p",          # standard body
        "article p",
        "div.article-body p",
        "div[data-dtm-region='articulo_cuerpo'] p",
    ]
    for selector in body_selectors:
        paragraphs = driver.find_elements(By.CSS_SELECTOR, selector)
        if paragraphs:
            text = " ".join(
                p.text.strip() for p in paragraphs if p.text.strip()
            )
            if text:
                return text[:600] + ("…" if len(text) > 600 else "")
    return "(Content not available)"


def _extract_image_url(driver) -> str | None:
    """Try several strategies to locate the article's cover image URL."""
    strategies = [
        # og:image meta
        lambda d: d.find_element(
            By.XPATH, "//meta[@property='og:image']"
        ).get_attribute("content"),
        # Article figure image
        lambda d: d.find_element(
            By.CSS_SELECTOR, "figure img"
        ).get_attribute("src"),
        # Generic hero image
        lambda d: d.find_element(
            By.CSS_SELECTOR, "div.a_m img"
        ).get_attribute("src"),
    ]
    for fn in strategies:
        try:
            url = fn(driver)
            if url and url.startswith("http"):
                return url
        except NoSuchElementException:
            continue
    return None


def _download_image(image_url: str, dest_dir: str, filename: str) -> str | None:
    """Download *image_url* to *dest_dir*/*filename*. Returns saved path or None."""
    os.makedirs(dest_dir, exist_ok=True)
    # Sanitise filename
    safe_name = re.sub(r"[^\w.\-]", "_", filename)[:80]
    dest_path = os.path.join(dest_dir, safe_name)
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; ElPaisScraper/1.0)"}
        resp = requests.get(image_url, headers=headers, timeout=15, stream=True)
        resp.raise_for_status()
        with open(dest_path, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=8192):
                fh.write(chunk)
        return dest_path
    except Exception as exc:
        print(f"  [scraper] Image download failed: {exc}")
        return None


# ── Main public function ─────────────────────────────────────────────────────

def run_scraper(driver, images_dir: str = IMAGE_DIR) -> dict:
    """
    Execute the full scrape pipeline on *driver*.
    Returns a dict with an "articles" list.
    """
    articles = []

    # Set a reasonable page-load timeout (30s) and eager strategy
    try:
        driver.set_page_load_timeout(30)
    except Exception:
        pass

    print("\n── Navigating to El País Opinion section ──────────────────────")
    driver.get(OPINION_URL)
    time.sleep(2)

    # Ensure Spanish locale by accepting the Spanish version
    _dismiss_consent(driver)
    time.sleep(1)

    print(f"  Page title: {driver.title}")
    print(f"  Current URL: {driver.current_url}\n")

    # ── Collect article URLs ─────────────────────────────────────────────────
    print("── Collecting article URLs ─────────────────────────────────────")
    article_urls = _extract_article_urls(driver)

    if not article_urls:
        print("  [ERROR] Could not find any article links on the Opinion page.")
        return {"articles": []}

    print(f"  Found {len(article_urls)} article URL(s).\n")

    # ── Scrape each article ──────────────────────────────────────────────────
    for idx, url in enumerate(article_urls, start=1):
        print(f"── Article {idx}/{len(article_urls)} ───────────────────────────────────────")
        print(f"  URL: {url}")

        try:
            driver.get(url)
            time.sleep(2)
            _dismiss_consent(driver)

            title = _extract_title(driver)
            content = _extract_content(driver)
            image_url = _extract_image_url(driver)

            # Download cover image
            image_path = None
            if image_url:
                ext = (image_url.split("?")[0].rsplit(".", 1) + ["jpg"])[-1]
                ext = ext if ext in ("jpg", "jpeg", "png", "webp", "gif") else "jpg"
                filename = f"article_{idx}_cover.{ext}"
                image_path = _download_image(image_url, images_dir, filename)

            # Print article info
            print(f"\n  📰 TÍTULO   : {title}")
            print(f"  🖼  IMAGEN   : {image_path or '(no image)'}")
            print(f"\n  CONTENIDO:\n  {content}\n")

            articles.append({
                "title": title,
                "content": content,
                "image": image_path,
                "url": url,
            })

        except WebDriverException as exc:
            print(f"  [scraper] WebDriver error on article {idx}: {exc}")
            continue

        time.sleep(random.uniform(1.0, 2.5))  # polite crawl delay

    return {"articles": articles}


# ── Local quick-test ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    from selenium.webdriver.chrome.options import Options

    opts = Options()
    opts.add_argument("--lang=es")
    opts.add_argument("--accept-lang=es")
    opts.add_experimental_option("prefs", {
        "intl.accept_languages": "es,es-ES",
    })
    # opts.add_argument("--headless=new")   # Uncomment to run headless

    drv = webdriver.Chrome(options=opts)
    drv.maximize_window()
    try:
        result = run_scraper(drv)
        print(f"\nScraped {len(result['articles'])} article(s).")
    finally:
        drv.quit()
