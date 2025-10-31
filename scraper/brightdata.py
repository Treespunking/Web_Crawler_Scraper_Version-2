# scraper/brightdata.py
import time
import requests
from typing import Optional
from .config import Config
from .logger import setup_logger

logger = setup_logger(__name__)


def fetch_via_brightdata(url: str) -> Optional[str]:
    """
    Fetch page HTML using Bright Data Web Unlocker API.
    Returns the raw HTML (string), not JSON.
    Includes exponential backoff with jitter and logging.
    """
    logger.info(f"🌐 Fetching via Bright Data: {url}")

    headers = {
        "Authorization": f"Bearer {Config.BRIGHTDATA_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "zone": "web_unlocker1",  # Adjust zone name per your Bright Data account
        "url": url,
        "format": "raw"           # 'raw' ensures Bright Data returns pure HTML
    }

    for attempt in range(1, Config.MAX_RETRIES + 1):
        try:
            response = requests.post(
                Config.BRIGHTDATA_API_URL,
                json=payload,
                headers=headers,
                timeout=60
            )

            # ✅ Successful request
            if response.status_code == 200:
                html = response.text.strip()
                if html and "<html" in html.lower():
                    logger.info(f"✅ Success on attempt {attempt}")
                    return html
                else:
                    logger.warning(f"⚠️ Empty or malformed HTML received on attempt {attempt}.")
            else:
                logger.warning(
                    f"⚠️ Bright Data returned {response.status_code}: "
                    f"{response.text[:200]}"
                )

        except Exception as e:
            logger.error(f"💥 Exception on attempt {attempt}: {str(e)}")

        # Retry with backoff + jitter
        if attempt < Config.MAX_RETRIES:
            delay = Config.calculate_retry_delay(attempt)
            logger.info(f"🔁 Retrying in {delay:.2f}s (attempt {attempt + 1}/{Config.MAX_RETRIES})...")
            time.sleep(delay)
        else:
            logger.error(f"❌ All {Config.MAX_RETRIES} attempts failed for {url}")

    return None
