# scraper/utils.py (improved)
import re
import asyncio
import random
from typing import Optional

def clean_price(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    # remove currency symbols, whitespace, non-digit except dot and comma
    cleaned = re.sub(r'[^\d.,]', '', text)
    # normalize commas -> dots if necessary (site-specific)
    cleaned = cleaned.replace(',', '.')
    return cleaned.strip() if cleaned else None

def extract_sold_count(text: Optional[str]) -> str:
    match = re.search(r'(\d+[,\d]*)', text or "")
    if not match:
        return "0"
    return match.group(1).replace(',', '')

async def random_delay(base: float, min_add: float, max_add: float):
    delay = base + random.uniform(min_add, max_add)
    await asyncio.sleep(delay)
