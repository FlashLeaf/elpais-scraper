# El País Opinion Scraper — Full Project Explanation

This document explains **every file**, **every class**, **every function**, and **every library** used in this project in plain, detailed language. It is meant to help you fully understand the codebase — whether for an interview, review, or learning.

---

## Project Structure Overview

```
elpais-scraper-main/
│
├── config.py                  # Central settings for the entire project
├── main.py                    # Entry point for local (your machine) run
├── browserstack_runner.py     # Entry point for parallel BrowserStack run
├── requirements.txt           # List of libraries to install
│
├── src/                       # Source code package
│   ├── __init__.py            # Marks src/ as a Python package
│   ├── scraper.py             # Scrapes articles from elpais.com
│   ├── translator.py          # Translates Spanish titles to English
│   └── analyzer.py            # Counts word frequency in translated titles
│
└── images/                    # Auto-created folder where cover images are saved
```

---

## How the Project Works (Big Picture)

```
main.py / browserstack_runner.py
        |
        v
   Build a Selenium WebDriver (Chrome locally, or Remote on BrowserStack)
        |
        v
   ElPaisScraper.scrape()       ← visits elpais.com/opinion, collects 5 articles
        |
        v
   ArticleTranslator.translate_all()  ← translates each Spanish title to English
        |
        v
   WordAnalyzer.print_report()  ← counts repeated words in translated titles
```

---

## 1. `requirements.txt` — What Needs to Be Installed

```
selenium>=4.18.0
requests>=2.31.0
Pillow>=10.0.0
python-dotenv>=1.0.0
```

### Why Each Library Is Needed

| Library | Why It Is Used |
|---|---|
| `selenium` | Controls a real web browser (Chrome, Firefox, Safari) to visit web pages, click buttons, and extract content — just like a human would. It is essential because El País requires JavaScript to render articles. |
| `requests` | Makes simple HTTP GET requests — used to download cover images from URLs and to call the MyMemory translation API. |
| `Pillow` | A Python image processing library. Listed as a dependency (future-proofing for image manipulation), though currently images are saved raw via `requests`. |
| `python-dotenv` | Reads a `.env` file from disk and loads its values as environment variables. Used to securely load `BROWSERSTACK_USERNAME` and `BROWSERSTACK_ACCESS_KEY` without hardcoding them in source code. |

### How to Install
```bash
pip install -r requirements.txt
```

---

## 2. `config.py` — Central Configuration

**Purpose:** One place to control all settings. None of the other files hardcode values like URLs or timeouts — they all import from `config.py`. This follows the **separation of concerns** principle.

### Headers / Imports Used

```python
from pathlib import Path   # Built-in Python module for working with file/folder paths in an OS-agnostic way
import os                  # Built-in — reads environment variables
from dotenv import load_dotenv   # From python-dotenv — loads .env file into os.environ
```

### Settings Explained

| Setting | Value | What It Does |
|---|---|---|
| `OPINION_URL` | `https://elpais.com/opinion/` | The URL the scraper navigates to first |
| `NUM_ARTICLES` | `5` | How many articles to scrape per session |
| `LANGUAGE` | `"es"` | Browser locale to set (Spanish) |
| `BASE_DIR` | current folder | Resolved to the folder where `config.py` lives using `Path(__file__).parent` |
| `IMAGES_DIR` | `BASE_DIR / "images"` | Where cover images get saved. `.mkdir(exist_ok=True)` auto-creates the folder if it doesn't exist |
| `PAGE_LOAD_TIMEOUT` | `30` | Seconds before Selenium gives up waiting for a page to load |
| `IMPLICIT_WAIT` | `10` | Seconds Selenium waits for an element to appear in the DOM |
| `WINDOW_SIZE` | `(1280, 900)` | Browser window resolution |
| `TRANSLATION_SOURCE` | `"es"` | Source language for translation API |
| `TRANSLATION_TARGET` | `"en"` | Target language for translation API |
| `REPEAT_THRESHOLD` | `2` | Words appearing MORE than this count are flagged as repeated |
| `BS_USERNAME` | from `.env` or hardcoded fallback | BrowserStack account username |
| `BS_ACCESS_KEY` | from `.env` or hardcoded fallback | BrowserStack secret access key |
| `BS_HUB_URL` | constructed URL | The remote WebDriver endpoint on BrowserStack's servers |
| `BS_CAPABILITIES` | list of 5 dicts | One dict per browser/device to test on (Chrome Win11, Firefox Win10, Safari macOS, Galaxy S23, iPhone 14) |

### Key Design Decision
`load_dotenv()` is called at module level, so the moment anyone imports `config`, the `.env` file is loaded automatically.

---

## 3. `src/__init__.py` — Package Marker

```python
# src package — El País Opinion Scraper modules
```

**Purpose:** This one-line file tells Python that the `src/` directory is a **package** — meaning you can do `from src.scraper import ElPaisScraper`. Without this file, Python would not recognise `src/` as importable.

**No imports are needed here.** It is intentionally minimal.

---

## 4. `src/scraper.py` — The Web Scraper

**Purpose:** Visits `elpais.com/opinion/`, collects up to 5 article URLs, visits each article, and extracts the title, body content snippet, and cover image.

### Headers / Imports Used

```python
import os        # Built-in — not actively used here, carried over from refactor
import re        # Built-in — regular expressions, used to validate article URLs by checking for date pattern (YYYY-MM-DD)
import time      # Built-in — used for sleep() delays between page loads (polite crawling)
import random    # Built-in — used to randomize crawl delays (1.0–2.0 seconds) to mimic human behaviour

import requests  # Third-party — downloads cover images via HTTP

from selenium.webdriver.common.by import By
# Selenium constant — defines how to find elements (By.CSS_SELECTOR, By.ID, By.XPATH, etc.)

from selenium.webdriver.support.ui import WebDriverWait
# Selenium — waits for a condition to be true before proceeding (smarter than time.sleep)

from selenium.webdriver.support import expected_conditions as EC
# Selenium — pre-built conditions like "element is clickable" or "element is present"

from selenium.common.exceptions import (
    TimeoutException,       # Raised when WebDriverWait runs out of time
    NoSuchElementException, # Raised when an element can not be found on page
    WebDriverException      # General Selenium error — used to catch network/driver failures
)

import config   # Our own config.py — settings like OPINION_URL, NUM_ARTICLES, etc.
```

### Class: `ElPaisScraper`

**Constructor `__init__(self, driver)`**
- Accepts an already-configured Selenium `driver` from outside.
- **Why pass the driver in?** So the same `ElPaisScraper` class works both locally AND on BrowserStack without any changes. This is the **Dependency Injection** pattern.
- Sets `page_load_timeout` from config.

---

**Method: `scrape()`** — The main public method
1. Calls `_go_to_opinion()` to navigate to the opinion page.
2. Calls `_collect_article_urls()` to gather 5 article URLs.
3. Loops through each URL, calling `_scrape_article()`.
4. Adds a random 1–2 second delay between articles (polite crawling).
5. Returns a list of article dicts: `{"title", "content", "image", "url"}`.

---

**Method: `_go_to_opinion()`**
- Navigates the browser to `config.OPINION_URL`.
- Waits 2 seconds for JavaScript to render.
- Calls `_dismiss_consent()` to handle the GDPR cookie banner.
- Prints the page title to confirm successful load.

---

**Method: `_dismiss_consent()`**
- El País shows a GDPR consent banner in the EU. The scraper tries 5 different selectors to find and click the "Accept" button:
  - `didomi-notice-agree-button` (the actual consent library they use)
  - XPath matching text "aceptar"
  - A CSS class selector
  - A generic "accept" class
  - English "Accept" text
- Uses `WebDriverWait(driver, 5)` — waits up to 5 seconds per attempt.
- If none work, it continues silently (banner may not appear in all regions).

---

**Method: `_collect_article_urls()`**
- Tries three CSS selectors to find article links: `"article h2 a"`, `"h2.c_t a"`, `"article a[href]"`.
- Falls back to scanning **all links on the page** (`<a>` tags) if fewer than 5 are found.
- Filters every URL with `_is_article_url()` before adding it.
- Uses a `seen` set to avoid duplicates.

---

**Static Method: `_is_article_url(href)`**
- Returns `True` only if the URL:
  - Is not empty
  - Contains `"elpais.com"`
  - Contains `"/opinion/"`
  - Contains a date in `YYYY-MM-DD` format (regex: `/\d{4}-\d{2}-\d{2}/`)
- **Why?** Section index pages like `/opinion/editoriales/` would otherwise be included and break the scraper.

---

**Method: `_scrape_article(url, idx)`**
- Navigates to the article URL, waits 2 seconds, dismisses consent.
- Calls `_extract_title()`, `_extract_content()`, `_extract_image_url()`, then `_download_image()`.
- Wraps everything in a `try/except WebDriverException` so one broken article does not crash the whole run.

---

**Method: `_extract_title()`**
- Tries CSS selectors `"h1.a_t"` then `"h1"`.
- Falls back to the `og:title` meta tag.
- Final fallback: `driver.title` (the browser tab title).

---

**Method: `_extract_content()`**
- Tries `"div.a_b p"`, `"article p"`, `"div.article-body p"` to get paragraph elements.
- Joins all paragraph texts, then truncates to 600 characters.

---

**Method: `_extract_image_url()`**
- Tries `og:image` meta tag first (most reliable).
- Falls back to `figure img` CSS selector.
- Returns `None` if neither is found.

---

**Method: `_download_image(image_url, idx)`**
- Uses `requests.get()` with a browser `User-Agent` header (to avoid being blocked).
- Streams the response in 8 KB chunks and writes to disk.
- Saves to `config.IMAGES_DIR / article_{idx}_cover.{ext}`.
- Returns the saved file path, or `None` on failure.

---

**Helper Method: `_find(css, timeout)`**
- A thin wrapper around `WebDriverWait + EC.presence_of_element_located`.
- Returns the element, or `None` if it times out (instead of raising an exception).

---

## 5. `src/translator.py` — Title Translator

**Purpose:** Takes a list of Spanish article titles and translates each one to English using the **free MyMemory REST API** (no API key required).

### Headers / Imports Used

```python
import time      # Built-in — adds a 0.5 second delay between API calls to be polite

import requests  # Third-party — makes HTTP GET requests to the MyMemory translation API

import config    # Our own config.py — TRANSLATION_SOURCE ("es") and TRANSLATION_TARGET ("en")
```

### Constant
```python
MYMEMORY_URL = "https://api.mymemory.translated.net/get"
```
This is the endpoint for the free MyMemory translation API. No signup is required.

---

### Class: `ArticleTranslator`

**Constructor `__init__(self, source, target)`**
- Defaults to Spanish → English from config.
- Builds `self.langpair = "es|en"` — the format the MyMemory API expects.

---

**Method: `translate(text, retries=3)`**
- Sends a GET request to MyMemory with three query parameters:
  - `q` — the text to translate
  - `langpair` — e.g. `"es|en"`
  - `de` — an email address. This increases the free-tier daily limit from 1,000 to 10,000 words on MyMemory.
- Retries up to 3 times on failure.
- Checks the response does not contain `"INVALID"` (MyMemory returns this string instead of throwing an error for bad input).
- Falls back to returning the original Spanish text if all retries fail.

---

**Method: `translate_all(titles)`**
- Loops through the list of titles, translates each, prints both the Spanish (`ES:`) and English (`EN:`) versions.
- Waits 0.5 seconds between each call to avoid rate-limiting.
- Returns a list of English translations in the same order as the input.

---

## 6. `src/analyzer.py` — Word Frequency Analyzer

**Purpose:** Takes a list of translated English titles, counts how often each word appears, and reports words that appear more than a threshold (default: 2 times).

### Headers / Imports Used

```python
import re                  # Built-in — splits text into word tokens using a regex that removes punctuation
from collections import Counter  # Built-in — a dict subclass that counts hashable objects efficiently

import config              # Our own config.py — REPEAT_THRESHOLD (default: 2)
```

### Module-Level Constant: `STOP_WORDS`

A hardcoded set of common English words to **ignore** during analysis:

```python
STOP_WORDS = {"a", "an", "the", "and", "or", "but", "in", "on", ...}
```

**Why?** Words like "the", "and", "is" appear in almost every sentence and would dominate the frequency list meaninglessly. Filtering them makes the analysis actually useful.

---

### Class: `WordAnalyzer`

**Constructor `__init__(self, threshold)`**
- `threshold` defaults to `config.REPEAT_THRESHOLD` (which is `2`).
- Stores the threshold — words must appear **strictly more than** this count to be reported.

---

**Method: `analyze(headers)`**
- Creates a `Counter` object.
- For each header, uses `re.split(r"[^a-zA-Z]+", header.lower())` to split on any non-letter character (spaces, punctuation, dashes, numbers).
- Filters out:
  - Empty strings (from leading/trailing punctuation)
  - Tokens shorter than 3 characters (removes "of", "35", etc.)
  - Stop words
- Updates the `Counter` with filtered tokens.
- Returns a `{word: count}` dict of only words exceeding the threshold.

---

**Method: `print_report(headers)`**
- Calls `analyze()`.
- If nothing is repeated: prints `"No words appear more than N time(s)."`.
- Otherwise prints a formatted table sorted by count (descending), then alphabetically.

---

## 7. `main.py` — Local Entry Point

**Purpose:** The file you run with `python main.py` on your own computer. It builds a local Chrome browser and runs the full pipeline.

### Headers / Imports Used

```python
import sys   # Built-in — used to reconfigure stdout encoding

# sys.stdout.reconfigure(encoding='utf-8') — forces the terminal to handle
# Spanish characters (accents, special letters) in article titles without crashing.
# Without this, Windows terminals using cp1252 encoding cause UnicodeEncodeError.

from selenium import webdriver                      # Third-party — core Selenium module
from selenium.webdriver.chrome.options import Options  # Chrome-specific settings

import config                             # Our central settings
from src.scraper    import ElPaisScraper  # The scraping class
from src.translator import ArticleTranslator  # The translation class
from src.analyzer   import WordAnalyzer   # The analysis class
```

---

### Function: `build_local_driver()`

Creates and returns a configured Chrome WebDriver:

```python
opts.page_load_strategy = "eager"
```
**Why "eager"?** Tells Chrome not to wait for every ad, image, and tracker to finish loading. The page is considered ready as soon as the main HTML is parsed. This prevents hanging on El País's many third-party resources.

```python
opts.add_argument("--lang=es")
opts.add_experimental_option("prefs", {"intl.accept_languages": "es,es-ES"})
```
**Why?** Forces Chrome to request pages in Spanish, so El País serves Spanish content rather than auto-detecting your locale and possibly redirecting.

```python
opts.add_argument("--disable-blink-features=AutomationControlled")
```
**Why?** Hides the fact that the browser is controlled by automation. Prevents El País from detecting a bot and blocking the session.

---

### Function: `run_pipeline(driver, session_label)`

The core orchestration function — called by both `main.py` and `browserstack_runner.py`:

1. **Step 1 — Scrape:** Creates `ElPaisScraper(driver)` and calls `.scrape()` to get a list of article dicts.
2. **Step 2 — Translate:** Creates `ArticleTranslator()` and calls `.translate_all()` on the Spanish titles. Adds `title_en` key to each article dict.
3. **Step 3 — Analyse:** Creates `WordAnalyzer()` and calls `.print_report()` on the English titles.
4. Returns the list of articles (so `browserstack_runner.py` can accumulate results).

---

### `if __name__ == "__main__":` Block

- Builds the local Chrome driver.
- Calls `run_pipeline()` in a `try/finally` block.
- `driver.quit()` in the `finally` block **always** closes the browser — even if the scraper crashes midway. This prevents zombie Chrome processes.

---

## 8. `browserstack_runner.py` — Parallel BrowserStack Run

**Purpose:** Runs the same `run_pipeline()` function on **5 different browsers and devices simultaneously** using BrowserStack Automate — a cloud-based testing platform. It uses Python threads to run all 5 sessions in parallel.

### Headers / Imports Used

```python
import threading  # Built-in — creates and manages parallel threads

from selenium import webdriver
from selenium.webdriver.chrome.options  import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
# Different browsers need different Options objects in Selenium.
# ChromeOptions is the default; FirefoxOptions is used for Firefox sessions.

import config          # Our settings — BS_HUB_URL, BS_CAPABILITIES, etc.
from main import run_pipeline  # Reuses the same pipeline function — no duplication
```

---

### Function: `build_bs_driver(caps)`

Builds a `webdriver.Remote` — a Selenium driver that connects to a **remote machine** (BrowserStack's cloud) instead of your local Chrome installation.

- Checks `browserName` to choose `ChromeOptions` vs `FirefoxOptions`.
- Sets all capabilities (OS, browser version, device name, session name, etc.) using `opts.set_capability()`.
- Connects to `config.BS_HUB_URL` — the BrowserStack hub endpoint which includes your username and access key embedded in the URL for authentication.

---

### Function: `run_session(caps, thread_num, results)`

This is the function each thread runs:

1. Extracts `sessionName` from `caps["bstack:options"]`.
2. Calls `build_bs_driver()` to open a remote browser.
3. Calls `run_pipeline()` — the exact same function as local mode.
4. Marks `status = "passed"` on success.
5. On any exception: logs the error, marks `status = "failed"`.
6. In the `finally` block:
   - Calls `driver.execute_script("browserstack_executor: ...")` — a special BrowserStack JavaScript command that marks the session as passed/failed in the BrowserStack dashboard.
   - Calls `driver.quit()` to close the remote session and stop billing.

---

### Function: `main()`

The orchestration for parallel execution:

**Starting threads:**
```python
for i, caps in enumerate(config.BS_CAPABILITIES, start=1):
    t = threading.Thread(target=run_session, args=(caps, i, results), daemon=True)
    threads.append(t)
    t.start()
```
- One thread per browser configuration (5 threads total).
- `daemon=True` — if the main program exits, threads are killed automatically.
- All 5 threads start nearly simultaneously → parallel execution.

**Waiting for completion:**
```python
for t in threads:
    t.join(timeout=600)
```
- `join()` blocks until the thread finishes (or 10 minutes elapses, whichever is first).
- All 5 threads are joined — main program waits for all to complete before printing results.

**Consolidated report:**
- Collects all English titles from all sessions into `all_titles_en`.
- Runs `WordAnalyzer().print_report()` on the combined list (5 sessions × 5 articles = 25 titles).
- Prints a final session summary table showing PASSED/FAILED per browser.

---

## Summary Table — All Files at a Glance

| File | Role | Key Dependencies |
|---|---|---|
| `requirements.txt` | Lists what to install with pip | — |
| `config.py` | Central settings — URLs, timeouts, BrowserStack creds, device list | `pathlib`, `os`, `dotenv` |
| `src/__init__.py` | Makes `src/` a Python package | — |
| `src/scraper.py` | Web scraping logic | `selenium`, `requests`, `re`, `time`, `random` |
| `src/translator.py` | Spanish → English via MyMemory API | `requests`, `time` |
| `src/analyzer.py` | Word frequency analysis | `re`, `collections.Counter` |
| `main.py` | Local Chrome run | `selenium`, `sys`, all `src/` modules |
| `browserstack_runner.py` | Parallel remote cloud run | `threading`, `selenium`, `main.run_pipeline` |

---

## Why Each Library Was Chosen

| Library | Alternative | Why This Choice |
|---|---|---|
| `selenium` | `playwright`, `scrapy` | BrowserStack Automate has native Selenium support; it is the industry standard for cross-browser automation testing |
| `requests` | `httpx`, `urllib` | Simple, battle-tested, synchronous HTTP client — perfect for single API calls and image downloads |
| `python-dotenv` | Hardcoding secrets | Keeps credentials out of source code; `.env` file is excluded from version control via `.gitignore` |
| `Pillow` | N/A | Required for any future image processing (resizing, format conversion); minimal overhead |
| `threading` | `multiprocessing`, `asyncio` | BrowserStack sessions are I/O-bound (waiting for network), not CPU-bound; threads are the simplest and most appropriate concurrency model here |
| `collections.Counter` | Manual dict counting | Purpose-built, efficient, readable — `Counter.update()` is cleaner than writing a nested loop |
| `pathlib.Path` | `os.path` | Modern, object-oriented path handling; works correctly on Windows, macOS, and Linux without needing to worry about `/` vs `\` |
