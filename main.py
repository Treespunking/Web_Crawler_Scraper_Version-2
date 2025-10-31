# main.py
import asyncio
from scraper.aliexpress_scraper import scrape_pages
from scraper.config import Config

if __name__ == "__main__":
    asyncio.run(
        scrape_pages(
            start_url=Config.START_URL,
            pages=Config.TOTAL_PAGES,
            concurrency=Config.CONCURRENCY_LIMIT,
            output_file=Config.OUTPUT_FILE
        )
    )
