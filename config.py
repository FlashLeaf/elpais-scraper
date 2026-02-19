"""
config.py
---------
Central configuration for the El País Opinion Scraper.
Edit this file to adjust behaviour without touching the source code.
"""
from pathlib import Path

# ── URLs ─────────────────────────────────────────────────────────────────────
OPINION_URL = "https://elpais.com/opinion/"

# ── Scraping ─────────────────────────────────────────────────────────────────
NUM_ARTICLES = 5          # Number of Opinion articles to scrape
LANGUAGE    = "es"        # Locale sent to the browser

# ── Output ────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
IMAGES_DIR = BASE_DIR / "images"
IMAGES_DIR.mkdir(exist_ok=True)

# ── Browser / Timeouts ───────────────────────────────────────────────────────
PAGE_LOAD_TIMEOUT = 30    # seconds before driver.get() gives up
IMPLICIT_WAIT     = 10    # seconds for implicit element waits
WINDOW_SIZE       = (1280, 900)

# ── Translation ───────────────────────────────────────────────────────────────
TRANSLATION_SOURCE = "es"
TRANSLATION_TARGET = "en"

# ── Word-frequency analysis ───────────────────────────────────────────────────
# Report words that appear STRICTLY MORE THAN this many times
REPEAT_THRESHOLD = 2

# ── BrowserStack ─────────────────────────────────────────────────────────────
import os
from dotenv import load_dotenv
load_dotenv()

BS_USERNAME   = os.getenv("BROWSERSTACK_USERNAME",   "nayanpaleja_TcfLVm")
BS_ACCESS_KEY = os.getenv("BROWSERSTACK_ACCESS_KEY", "zVftqsPjyf83o9RZ43Gq")
BS_HUB_URL    = f"https://{BS_USERNAME}:{BS_ACCESS_KEY}@hub.browserstack.com/wd/hub"
BS_PROJECT    = "ElPais Scraper"
BS_BUILD      = "elpais-opinion-scrape"

# 5 browser/device combinations (3 desktop + 2 real mobile)
BS_CAPABILITIES = [
    {   # 1 — Desktop Chrome / Windows 11
        "browserName": "Chrome",
        "bstack:options": {
            "os": "Windows", "osVersion": "11",
            "browserVersion": "latest",
            "sessionName": "Chrome Win11",
            "projectName": BS_PROJECT, "buildName": BS_BUILD,
        },
    },
    {   # 2 — Desktop Firefox / Windows 10
        "browserName": "Firefox",
        "bstack:options": {
            "os": "Windows", "osVersion": "10",
            "browserVersion": "latest",
            "sessionName": "Firefox Win10",
            "projectName": BS_PROJECT, "buildName": BS_BUILD,
        },
    },
    {   # 3 — Desktop Safari / macOS Ventura
        "browserName": "Safari",
        "bstack:options": {
            "os": "OS X", "osVersion": "Ventura",
            "browserVersion": "latest",
            "sessionName": "Safari macOS Ventura",
            "projectName": BS_PROJECT, "buildName": BS_BUILD,
        },
    },
    {   # 4 — Real mobile: Samsung Galaxy S23 / Android
        "browserName": "Chrome",
        "bstack:options": {
            "deviceName": "Samsung Galaxy S23", "osVersion": "13.0",
            "realMobile": "true",
            "sessionName": "Galaxy S23 Chrome",
            "projectName": BS_PROJECT, "buildName": BS_BUILD,
        },
    },
    {   # 5 — Real mobile: iPhone 14 / iOS Safari
        "browserName": "Safari",
        "bstack:options": {
            "deviceName": "iPhone 14", "osVersion": "16",
            "realMobile": "true",
            "sessionName": "iPhone 14 Safari",
            "projectName": BS_PROJECT, "buildName": BS_BUILD,
        },
    },
]
