# scraper/config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """
    Central configuration class for AliExpress scraper.
    Handles scraper behavior, browser settings, concurrency,
    throttling, retry backoff (with cap), and output management.
    """
    # === Bright Data API Configuration ===
    BRIGHTDATA_API_KEY = os.getenv("BRIGHTDATA_API_KEY")
    BRIGHTDATA_API_URL = os.getenv("BRIGHTDATA_API_URL", "https://api.brightdata.com/request")

    if not BRIGHTDATA_API_KEY:
        raise ValueError("⚠️ Missing BRIGHTDATA_API_KEY in .env file")
    
    # === Scraper Settings ===
    START_URL = os.getenv(
        "START_URL",
        "https://www.aliexpress.com/w/wholesale-phone-watch.html?SearchText=phone+watch&page=1"
    )

    # Number of category pages to scrape (default = 6)
    TOTAL_PAGES = int(os.getenv("TOTAL_PAGES", "6"))

    # Concurrency — number of pages processed in parallel
    CONCURRENCY_LIMIT = int(os.getenv("CONCURRENCY_LIMIT", "3"))

    # Number of retry attempts per page in case of Bright Data or parsing errors
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

    # Timeouts (in milliseconds)
    PAGE_LOAD_TIMEOUT = int(os.getenv("PAGE_LOAD_TIMEOUT", "30000"))

    # === Throttling & Anti-Ban Settings ===
    BASE_DELAY = float(os.getenv("BASE_DELAY", "2.0"))  # base delay before each page
    RANDOM_DELAY_RANGE = (
        float(os.getenv("RANDOM_DELAY_MIN", "0.5")),
        float(os.getenv("RANDOM_DELAY_MAX", "1.5"))
    )

    # === Retry Backoff Settings ===
    RETRY_BASE_DELAY = float(os.getenv("RETRY_BASE_DELAY", "2.0"))       # Initial wait before first retry
    RETRY_BACKOFF_FACTOR = float(os.getenv("RETRY_BACKOFF_FACTOR", "2"))  # Multiplier (exponential)
    RETRY_JITTER = float(os.getenv("RETRY_JITTER", "1.0"))               # Random jitter to avoid synchronization
    RETRY_MAX_DELAY = float(os.getenv("RETRY_MAX_DELAY", "30.0"))        # Cap maximum delay between retries (in seconds)

    # === Output ===
    OUTPUT_FILE = os.getenv("OUTPUT_FILE", "aliexpress_products.json")

    # Optional NDJSON output toggle (True = append line-by-line)
    USE_NDJSON = bool(int(os.getenv("USE_NDJSON", "1")))

    # === Browser Settings ===
    HEADLESS = bool(int(os.getenv("HEADLESS", "1")))
    VIEWPORT = {"width": 1366, "height": 768}
    USER_AGENT = os.getenv(
        "USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    )

    # === Logging ===
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # === Helper Method for Backoff Calculation ===
    @classmethod
    def calculate_retry_delay(cls, attempt: int) -> float:
        """
        Calculate exponential backoff delay with jitter and cap.
        Example:
            attempt = 1 → 2s
            attempt = 2 → 4s
            attempt = 3 → 8s (but capped to RETRY_MAX_DELAY)
        """
        from random import uniform
        delay = cls.RETRY_BASE_DELAY * (cls.RETRY_BACKOFF_FACTOR ** (attempt - 1))
        delay = min(delay + uniform(0, cls.RETRY_JITTER), cls.RETRY_MAX_DELAY)
        return round(delay, 2)

    @classmethod
    def summary(cls) -> str:
        """Return a readable summary of key configuration for debugging."""
        return (
            f"🌐 START_URL: {cls.START_URL}\n"
            f"📄 TOTAL_PAGES: {cls.TOTAL_PAGES}\n"
            f"⚙️  CONCURRENCY_LIMIT: {cls.CONCURRENCY_LIMIT}\n"
            f"🔁 MAX_RETRIES: {cls.MAX_RETRIES}\n"
            f"⏱️ RETRY_BACKOFF: base={cls.RETRY_BASE_DELAY}s, "
            f"factor={cls.RETRY_BACKOFF_FACTOR}, jitter={cls.RETRY_JITTER}s, "
            f"cap={cls.RETRY_MAX_DELAY}s\n"
            f"💾 OUTPUT_FILE: {cls.OUTPUT_FILE}\n"
            f"⏳ BASE_DELAY: {cls.BASE_DELAY}s ± {cls.RANDOM_DELAY_RANGE}\n"
            f"🧠 HEADLESS: {cls.HEADLESS}\n"
            f"🪶 USER_AGENT: {cls.USER_AGENT[:60]}..."
        )


if __name__ == "__main__":
    # Print configuration summary for quick debugging
    print(Config.summary())
    print("\nRetry delay simulation:")
    for i in range(1, 6):
        print(f"  Attempt {i}: {Config.calculate_retry_delay(i)}s")
