# El País Opinion Scraper

A Python + Selenium web scraper that:
1. Visits [El País](https://elpais.com/opinion/) in Spanish
2. Scrapes the **first 5 Opinion articles** (title, content, cover image)
3. **Translates** article titles from Spanish → English via MyMemory API
4. **Analyses** word frequency in translated titles (words appearing > 2 times)
5. Runs in **5 parallel threads** on BrowserStack (3 desktop + 2 mobile)

---

## Project Structure

```
elpais-scraper/
├── scraper.py               # Core scraping logic
├── translator.py            # MyMemory / Google Translate helper
├── analyzer.py              # Word-frequency analysis
├── browserstack_local.py    # Local run entry point
├── browserstack_runner.py   # BrowserStack parallel run (5 threads)
├── requirements.txt
├── .env                     # Your credentials (do not commit!)
├── .env.example             # Template
└── images/                  # Downloaded cover images (auto-created)
```

---

## Setup

### 1. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 2. Configure Environment
Copy `.env.example` to `.env` (already done) and ensure credentials are filled in:
```
BROWSERSTACK_USERNAME=nayanpaleja_TcfLVm
BROWSERSTACK_ACCESS_KEY=zVftqsPjyf83o9RZ43Gq
```

### 3. Install ChromeDriver
Selenium 4.18+ auto-manages ChromeDriver via Selenium Manager — no manual install needed.

---

## Running Locally

```powershell
python browserstack_local.py
```

**Expected output:**
- 5 article titles + content snippets (in Spanish)
- 5 translated English titles
- Word-frequency table (words appearing > 2 times)
- Cover images saved to `images/`

---

## Running on BrowserStack (5 Parallel Threads)

```powershell
python browserstack_runner.py
```

**Browser/Device matrix:**

| # | Configuration | Type |
|---|--------------|------|
| 1 | Chrome latest / Windows 11 | Desktop |
| 2 | Firefox latest / Windows 10 | Desktop |
| 3 | Safari latest / macOS Ventura | Desktop |
| 4 | Samsung Galaxy S23 / Chrome | Mobile Android |
| 5 | iPhone 14 / Safari | Mobile iOS |

Sessions are visible in your [BrowserStack Automate dashboard](https://automate.browserstack.com/).

---

## Translation API

Uses the **free [MyMemory API](https://mymemory.translated.net/)** — no key required.  
To use Google Cloud Translation instead, set `GOOGLE_API_KEY` in `.env`.

---

## Notes

- El País may show a GDPR consent banner — the scraper handles it automatically.
- Cover images are saved to `images/article_N_cover.jpg`.
- BrowserStack sessions are automatically marked **passed** or **failed**.
