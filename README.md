# AliExpress Product Scraper 

A robust, production-ready web scraper to extract product data from AliExpress using **Playwright + Bright Data Web Unlocker API** to bypass anti-bot protections. Features concurrent page scraping, exponential backoff, NDJSON output, and comprehensive error handling.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Playwright](https://img.shields.io/badge/Tool-Playwright-purple)
![BrightData](https://img.shields.io/badge/Proxy-BrightData-orange)

---

## Features

- **Anti-Bot Bypass**: Uses Bright Data Web Unlocker API to fetch HTML and bypass AliExpress protections
- **Concurrent Scraping**: Configurable concurrency with semaphore-based rate limiting
- **Smart Retry Logic**: Exponential backoff with jitter and configurable max delay caps
- **Comprehensive Data Extraction**: Scrapes product titles, prices, ratings, sales count, thumbnails, URLs, and product IDs
- **NDJSON Output**: Incremental line-by-line JSON append to avoid data loss
- **Duplicate Prevention**: Tracks seen URLs to avoid re-scraping existing products
- **Progress Tracking**: Real-time progress bar using `tqdm`
- **Debug-Friendly**: Saves failed page HTML for troubleshooting
- **Modular Architecture**: Clean separation of concerns with logging, config, and utilities

---

## Requirements

- **Python 3.8+**
- **Node.js** (for Playwright browser binaries)
- **Bright Data account** with Web Unlocker API access

---

## Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/Treespunking/Web_Crawler_Scraper.git
cd Web_Crawler_Scraper
```

### 2. Set up virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

**Requirements:**
```txt
playwright
requests
python-dotenv
tqdm
```

### 4. Install Playwright browser binaries
```bash
playwright install chromium
```

### 5. Configure environment variables

Create a `.env` file in the project root:

```env
# === Bright Data API ===
BRIGHTDATA_API_KEY=your_web_unlocker_api_key_here
BRIGHTDATA_API_URL=https://api.brightdata.com/request

# === Scraper Settings ===
START_URL=https://www.aliexpress.com/w/wholesale-phone-watch.html?SearchText=phone+watch&page=1
TOTAL_PAGES=6
CONCURRENCY_LIMIT=3
MAX_RETRIES=3

# === Timing & Throttling ===
BASE_DELAY=2.0
RANDOM_DELAY_MIN=0.5
RANDOM_DELAY_MAX=1.5

# === Retry Backoff ===
RETRY_BASE_DELAY=2.0
RETRY_BACKOFF_FACTOR=2
RETRY_JITTER=1.0
RETRY_MAX_DELAY=30.0

# === Output ===
OUTPUT_FILE=aliexpress_products.json
USE_NDJSON=1

# === Browser ===
HEADLESS=1
USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36

# === Logging ===
LOG_LEVEL=INFO
```

> ⚠️ **Security Note**: Never commit `.env` to version control! Add it to `.gitignore`.

---

## Usage

### Basic Usage
```bash
python -m scraper.aliexpress_scraper
```

### Advanced Usage with Arguments
```bash
python -m scraper.aliexpress_scraper \
  --pages 10 \
  --concurrency 5 \
  --output data/products.json \
  --start-url "https://www.aliexpress.com/w/wholesale-phone-watch.html?SearchText=phone+watch&page=1"
```

**Available Arguments:**
- `--pages`: Number of pages to scrape (default: 6)
- `--concurrency`: Concurrent page requests (default: 3)
- `--output`: Output file path (default: `aliexpress_products.json`)
- `--start-url`: Starting category URL (default: from `.env`)

---

## Data Output

### NDJSON Format (Newline-Delimited JSON)
Each line is a valid JSON object representing one product:

```json
{"product_title": "Smart Watch Phone", "product_url": "https://www.aliexpress.com/item/1234567890.html", "product_id": "1234567890", "price": "29.99", "amount_sold": "500+ sold", "amount_sold_count": "500", "product_rating": "4.5", "product_thumbnail": "https://..."}
{"product_title": "Another Product", "product_url": "https://...", "product_id": "...", ...}
```

### Extracted Fields
- `product_title`: Product name
- `product_url`: Direct link to product page
- `product_id`: Unique AliExpress product ID
- `price`: Cleaned price (numeric string)
- `amount_sold`: Raw sales text (e.g., "500+ sold")
- `amount_sold_count`: Parsed numeric sales count
- `product_rating`: Star rating (if available)
- `product_thumbnail`: Product image URL

---

## Explore Data with EDA

Analyze scraped data interactively using Jupyter:

```bash
jupyter notebook EDA.ipynb
```

**Included Visualizations:**
- Price distribution histograms
- Top-selling products by category
- Correlation between ratings and sales
- Price vs. sales trends

---

## Project Structure

```
Web_Crawler_Scraper/
│
├── main.py                       # Main entry point (if needed)
├── aliexpress_products.json      # Output file (NDJSON)
├── EDA.ipynb                     # Data analysis notebook
├── .env                          # Environment variables (DO NOT COMMIT)
├── .gitignore                    # Git ignore file
├── requirements.txt              # Python dependencies
│
└── scraper/
    ├── __init__.py
    ├── config.py                 # Configuration & environment loader
    ├── logger.py                 # Logging setup
    ├── utils.py                  # Helper functions (price cleaning, delays)
    ├── brightdata.py             # Bright Data API wrapper with retries
    └── aliexpress_scraper.py     # Core scraping logic with concurrency
```

---

## Configuration Deep Dive

### Key Config Parameters (in `config.py`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `TOTAL_PAGES` | 6 | Number of category pages to scrape |
| `CONCURRENCY_LIMIT` | 3 | Max parallel page requests |
| `MAX_RETRIES` | 3 | Retry attempts per page on failure |
| `BASE_DELAY` | 2.0s | Base delay between page fetches |
| `RETRY_BASE_DELAY` | 2.0s | Initial retry wait time |
| `RETRY_BACKOFF_FACTOR` | 2 | Exponential multiplier (2^attempt) |
| `RETRY_MAX_DELAY` | 30.0s | Maximum retry delay cap |
| `USE_NDJSON` | 1 | Enable line-by-line JSON output |

### Retry Logic Example
```
Attempt 1: 2.0s delay
Attempt 2: 4.0s delay  (2 * 2^1)
Attempt 3: 8.0s delay  (2 * 2^2)
Attempt 4: 16.0s delay (capped if > RETRY_MAX_DELAY)
```

---

## How It Works

1. **URL Generation**: Builds paginated URLs by appending `?page=N` query params
2. **Bright Data Fetch**: Sends URL to Bright Data API, receives raw HTML
3. **Playwright Parsing**: Loads HTML into Playwright browser context for DOM parsing
4. **Product Extraction**: Uses resilient CSS selectors to extract product data via JavaScript
5. **Data Cleaning**: Cleans prices, extracts numeric sold counts, validates URLs
6. **Deduplication**: Checks against existing URLs before saving
7. **NDJSON Append**: Writes new products incrementally to output file
8. **Concurrency Control**: Semaphore limits parallel requests to avoid rate limits
9. **Error Handling**: Exponential backoff with jitter on failures

---

## Debugging

### View Configuration Summary
```bash
python -m scraper.config
```

### Debug Failed Pages
When scraping fails, check:
- `last_fetched_page.html` - Last successfully fetched HTML
- `debug_failed_page.html` - HTML from failed parsing attempts

### Enable Verbose Logging
Set in `.env`:
```env
LOG_LEVEL=DEBUG
```

---