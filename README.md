# El País Opinion Scraper 🗞️

A Selenium-based web scraper that extracts articles from [El País Opinion](https://elpais.com/opinion/), translates their titles to English, and analyses word frequency — running in parallel across **5 browser/device combinations** on BrowserStack.

---

## Project Structure

```
elpais-scraper/
├── src/
│   ├── scraper.py          # ElPaisScraper class
│   ├── translator.py       # ArticleTranslator class (MyMemory API)
│   └── analyzer.py         # WordAnalyzer class
├── config.py               # All settings in one place
├── main.py                 # Local run entry point
├── browserstack_runner.py  # BrowserStack parallel runner (5 threads)
├── requirements.txt
├── .env                    # BrowserStack credentials (git-ignored)
└── .env.example
```

---

## How It Works

### 1 · Scrape (`ElPaisScraper`)
- Navigates to `elpais.com/opinion/` with the browser set to **Spanish locale**
- Handles the GDPR consent banner automatically
- Filters article URLs using a date-regex (`/YYYY-MM-DD/`) to avoid scraping section indexes
- Extracts **title**, **content snippet**, and **cover image** for each of the first 5 articles

### 2 · Translate (`ArticleTranslator`)
- Calls the **free MyMemory REST API** (no key required) to translate ES → EN
- Retries up to 3 times on failure; falls back to original text

### 3 · Analyse (`WordAnalyzer`)
- Tokenises all translated titles and counts word frequencies
- Reports words appearing **more than twice**

### 4 · BrowserStack Parallel Run (`browserstack_runner.py`)
- Spawns **5 threads** simultaneously, one per browser/device:

| # | Browser | OS / Device |
|---|---------|------------|
| 1 | Chrome latest | Windows 11 |
| 2 | Firefox latest | Windows 10 |
| 3 | Safari latest | macOS Ventura |
| 4 | Chrome | Samsung Galaxy S23 (real device) |
| 5 | Safari | iPhone 14 (real device) |

- Each session is marked **passed/failed** in the BrowserStack Automate dashboard

---

## Setup

```bash
# 1. Clone and install dependencies
pip install -r requirements.txt

# 2. Copy credentials template
cp .env.example .env
# Fill in BROWSERSTACK_USERNAME and BROWSERSTACK_ACCESS_KEY
```

## Running

```bash
# Local Chrome run
python main.py

# BrowserStack parallel run (5 browsers at once)
python browserstack_runner.py
```

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| selenium | 4.18+ | Browser automation |
| requests | 2.31+ | API calls + image downloads |
| Pillow | 10.0+ | Image handling |
| python-dotenv | 1.0+ | Load `.env` credentials |
