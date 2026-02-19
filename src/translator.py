"""
src/translator.py
-----------------
ArticleTranslator — translates Spanish titles to English.

Uses the free MyMemory REST API (no API key required).
Falls back to the original text if translation fails.
"""

import time
import requests

import config


MYMEMORY_URL = "https://api.mymemory.translated.net/get"


class ArticleTranslator:
    """Translates article titles from Spanish to English via MyMemory API."""

    def __init__(
        self,
        source: str = config.TRANSLATION_SOURCE,
        target: str = config.TRANSLATION_TARGET,
    ):
        self.langpair = f"{source}|{target}"

    def translate(self, text: str, retries: int = 3) -> str:
        """Translate a single text string. Returns original text on failure."""
        if not text:
            return text

        params = {
            "q":        text,
            "langpair": self.langpair,
            "de":       "nayanpaleja5@gmail.com",   # improves free-tier rate limit
        }

        for attempt in range(1, retries + 1):
            try:
                resp = requests.get(MYMEMORY_URL, params=params, timeout=10)
                resp.raise_for_status()
                translated = resp.json()["responseData"]["translatedText"]
                if translated and "INVALID" not in translated.upper():
                    return translated
            except Exception as exc:
                print(f"  [translator] Attempt {attempt} failed: {exc}")
                time.sleep(1)

        return text     # fallback: return original

    def translate_all(self, titles: list[str]) -> list[str]:
        """Translate a list of titles, printing each pair."""
        results = []
        for i, title in enumerate(titles, start=1):
            print(f"  [{i}] ES: {title}")
            en = self.translate(title)
            print(f"       EN: {en}")
            results.append(en)
            time.sleep(0.5)   # be polite to the free API
        return results
