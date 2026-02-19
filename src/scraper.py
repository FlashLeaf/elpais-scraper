"""
src/scraper.py
--------------
ElPaisScraper — scrapes the Opinion section of elpais.com.

Design decisions (good to mention in interview):
  - Accepts an external driver so the same class works locally AND on BrowserStack
  - Date-regex URL filter avoids scraping section-index pages (e.g. /opinion/editoriales/)
  - Consent-banner handling tries multiple selectors for robustness
  - page_load_strategy='eager' prevents hanging on slow ad-heavy pages
"""

import os
import re
import time
import random
import requests

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException
)

import config


class ElPaisScraper:
    """Scrapes El País Opinion articles: title, content snippet, and cover image."""

    def __init__(self, driver):
        """
        Args:
            driver: A pre-configured Selenium WebDriver (local Chrome or
                    BrowserStack Remote). Keeping driver creation outside this
                    class makes it easy to swap or mock in tests.
        """
        self.driver = driver
        self.driver.set_page_load_timeout(config.PAGE_LOAD_TIMEOUT)

    # ── Public API ────────────────────────────────────────────────────────────

    def scrape(self) -> list[dict]:
        """
        Full scrape pipeline. Returns a list of article dicts:
            {"title": str, "content": str, "image": str|None, "url": str}
        """
        self._go_to_opinion()
        urls = self._collect_article_urls()
        articles = []
        for idx, url in enumerate(urls, start=1):
            article = self._scrape_article(url, idx)
            if article:
                articles.append(article)
            time.sleep(random.uniform(1.0, 2.0))   # polite crawl delay
        return articles

    # ── Navigation ────────────────────────────────────────────────────────────

    def _go_to_opinion(self):
        print(f"\n  Navigating → {config.OPINION_URL}")
        self.driver.get(config.OPINION_URL)
        time.sleep(2)
        self._dismiss_consent()
        print(f"  Page title : {self.driver.title}")

    def _dismiss_consent(self):
        """Try common GDPR consent-button selectors."""
        selectors = [
            (By.ID,          "didomi-notice-agree-button"),
            (By.XPATH,       "//button[contains(translate(text(),'ACEPTAR','aceptar'),'aceptar')]"),
            (By.CSS_SELECTOR, "button.css-1ynyhfy"),
            (By.XPATH,       "//button[contains(@class,'accept')]"),
            (By.XPATH,       "//button[contains(text(),'Accept')]"),
        ]
        for by, value in selectors:
            try:
                btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((by, value))
                )
                btn.click()
                time.sleep(1.5)
                print("  Consent banner dismissed.")
                return
            except (TimeoutException, NoSuchElementException, WebDriverException):
                continue
        print("  No consent banner found.")

    # ── URL collection ────────────────────────────────────────────────────────

    def _collect_article_urls(self) -> list[str]:
        """Return up to NUM_ARTICLES real article URLs (must contain a date slug)."""
        seen, urls = set(), []
        css_selectors = ["article h2 a", "h2.c_t a", "article a[href]"]

        for selector in css_selectors:
            for el in self.driver.find_elements(By.CSS_SELECTOR, selector):
                href = el.get_attribute("href") or ""
                if self._is_article_url(href) and href not in seen:
                    seen.add(href)
                    urls.append(href)
                if len(urls) >= config.NUM_ARTICLES:
                    break
            if len(urls) >= config.NUM_ARTICLES:
                break

        # Fallback: scan all page links
        if len(urls) < config.NUM_ARTICLES:
            for el in self.driver.find_elements(By.TAG_NAME, "a"):
                href = el.get_attribute("href") or ""
                if self._is_article_url(href) and href not in seen:
                    seen.add(href)
                    urls.append(href)
                if len(urls) >= config.NUM_ARTICLES:
                    break

        print(f"  Found {len(urls)} article URL(s).")
        return urls

    @staticmethod
    def _is_article_url(href: str) -> bool:
        """Only accept URLs with a YYYY-MM-DD date segment (real articles)."""
        return (
            bool(href)
            and "elpais.com" in href
            and "/opinion/" in href
            and bool(re.search(r"/\d{4}-\d{2}-\d{2}/", href))
        )

    # ── Per-article scraping ──────────────────────────────────────────────────

    def _scrape_article(self, url: str, idx: int) -> dict | None:
        print(f"\n  [{idx}/{config.NUM_ARTICLES}] {url}")
        try:
            self.driver.get(url)
            time.sleep(2)
            self._dismiss_consent()

            title   = self._extract_title()
            content = self._extract_content()
            image   = self._download_image(self._extract_image_url(), idx)

            print(f"  📰 {title}")
            print(f"  🖼  Image: {image or '(none)'}")
            return {"title": title, "content": content, "image": image, "url": url}

        except WebDriverException as exc:
            print(f"  ⚠ WebDriver error: {exc.msg[:120]}")
            return None

    def _extract_title(self) -> str:
        for selector in ["h1.a_t", "h1"]:
            el = self._find(selector, timeout=6)
            if el and el.text.strip():
                return el.text.strip()
        try:
            return self.driver.find_element(
                By.XPATH, "//meta[@property='og:title']"
            ).get_attribute("content").strip()
        except NoSuchElementException:
            return self.driver.title.strip()

    def _extract_content(self) -> str:
        for selector in ["div.a_b p", "article p", "div.article-body p"]:
            paras = self.driver.find_elements(By.CSS_SELECTOR, selector)
            text  = " ".join(p.text.strip() for p in paras if p.text.strip())
            if text:
                return text[:600] + ("…" if len(text) > 600 else "")
        return "(Content not available)"

    def _extract_image_url(self) -> str | None:
        attempts = [
            lambda: self.driver.find_element(
                By.XPATH, "//meta[@property='og:image']"
            ).get_attribute("content"),
            lambda: self.driver.find_element(
                By.CSS_SELECTOR, "figure img"
            ).get_attribute("src"),
        ]
        for fn in attempts:
            try:
                url = fn()
                if url and url.startswith("http"):
                    return url
            except NoSuchElementException:
                continue
        return None

    def _download_image(self, image_url: str | None, idx: int) -> str | None:
        if not image_url:
            return None
        ext  = image_url.split("?")[0].rsplit(".", 1)[-1]
        ext  = ext if ext in ("jpg", "jpeg", "png", "webp") else "jpg"
        path = config.IMAGES_DIR / f"article_{idx}_cover.{ext}"
        try:
            resp = requests.get(
                image_url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15, stream=True
            )
            resp.raise_for_status()
            with open(path, "wb") as f:
                for chunk in resp.iter_content(8192):
                    f.write(chunk)
            return str(path)
        except Exception as exc:
            print(f"  Image download failed: {exc}")
            return None

    # ── Helper ────────────────────────────────────────────────────────────────

    def _find(self, css: str, timeout: int = config.IMPLICIT_WAIT):
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, css))
            )
        except TimeoutException:
            return None
