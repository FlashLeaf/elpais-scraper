"""
translator.py
-------------
Translates Spanish text to English using the free MyMemory API.
No API key required for low-volume usage (~1000 words/day per IP).

If a GOOGLE_API_KEY environment variable is set, it switches to
the Google Cloud Translation REST API automatically.
"""

import os
import time
import requests

MYMEMORY_URL = "https://api.mymemory.translated.net/get"
GOOGLE_URL = "https://translation.googleapis.com/language/translate/v2"


def translate_es_to_en(text: str) -> str:
    """
    Translate *text* from Spanish to English.
    Uses Google Translate if GOOGLE_API_KEY is set, otherwise MyMemory.
    """
    google_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if google_key:
        return _google_translate(text, google_key)
    return _mymemory_translate(text)


# ── MyMemory (free) ──────────────────────────────────────────────────────────

def _mymemory_translate(text: str, retries: int = 3) -> str:
    params = {
        "q": text,
        "langpair": "es|en",
        "de": "nayanpaleja5@gmail.com",   # Optional email improves rate limit
    }
    for attempt in range(retries):
        try:
            resp = requests.get(MYMEMORY_URL, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            translated = data.get("responseData", {}).get("translatedText", "")
            if translated and translated.upper() != "INVALID LANGUAGE PAIR SPECIFIED":
                return translated
        except requests.RequestException as exc:
            print(f"  [translator] MyMemory attempt {attempt + 1} failed: {exc}")
            time.sleep(1.5)
    # Fallback: return original text
    return text


# ── Google Cloud Translation REST API ────────────────────────────────────────

def _google_translate(text: str, api_key: str) -> str:
    params = {
        "q": text,
        "source": "es",
        "target": "en",
        "key": api_key,
        "format": "text",
    }
    try:
        resp = requests.post(GOOGLE_URL, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()["data"]["translations"][0]["translatedText"]
    except Exception as exc:
        print(f"  [translator] Google Translate failed: {exc} — falling back to MyMemory")
        return _mymemory_translate(text)


if __name__ == "__main__":
    samples = [
        "La crisis política en Europa",
        "El futuro de la inteligencia artificial",
        "Democracia y libertad de prensa",
    ]
    for s in samples:
        print(f"  ES: {s}")
        print(f"  EN: {translate_es_to_en(s)}\n")
