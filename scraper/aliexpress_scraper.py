# scraper/aliexpress_scraper.py
import asyncio
import json
from typing import List, Dict
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse
from playwright.async_api import async_playwright, Browser, Page
from tqdm.asyncio import tqdm_asyncio

from .config import Config
from .logger import setup_logger
from .utils import clean_price, extract_sold_count, random_delay
from .brightdata import fetch_via_brightdata

logger = setup_logger(__name__)
DEFAULT_TIMEOUT = 30000  # 30 seconds — safer for slow network/pages


def with_page_param(url: str, page_num: int) -> str:
    """Append or update 'page' query param for AliExpress URLs."""
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    qs["page"] = [str(page_num)]
    new_query = urlencode({k: v[0] for k, v in qs.items()})
    new_parsed = parsed._replace(query=new_query)
    return urlunparse(new_parsed)


async def parse_products_from_page(page: Page) -> List[Dict]:
    """Extract all product info from the AliExpress category page."""
    selector = 'a[href*=".html"][href*="/item/"]'  # resilient generic selector

    raw_products = await page.eval_on_selector_all(selector, '''
        (cards) => {
            return cards.map(card => {
                const titleElem = card.querySelector('h3, .multi--titleText--nXeOv, [class*="title"]');
                const title = titleElem?.innerText?.trim() || "N/A";

                let productUrl = card.href;
                if (productUrl?.startsWith("//")) {
                    productUrl = "https:" + productUrl;
                }

                const priceElem = card.querySelector('[class*="price"], [class*="Price"], [class*="currency"]');
                const price = priceElem?.innerText?.trim() || null;

                const soldElem = card.querySelector('[class*="sold"], [class*="Sale"], [class*="orders"]');
                const amountSold = soldElem?.innerText?.trim() || "0 sold";

                const ratingElem = card.querySelector('[class*="rating"], [class*="star"]');
                const productRating = ratingElem?.innerText?.trim() || null;

                const img = card.querySelector('img');
                const thumbnail = img?.src || img?.dataset?.src || null;

                let product_id = null;
                try {
                    const m = productUrl && productUrl.match(/\\/item\\/(\\d+)\\.html/);
                    product_id = m ? m[1] : null;
                } catch (e) {}

                return {
                    product_title: title,
                    product_url: productUrl,
                    product_id: product_id,
                    price: price,
                    amount_sold: amountSold,
                    amount_sold_count: amountSold,
                    product_rating: productRating,
                    product_thumbnail: thumbnail
                };
            });
        }
    ''')

    for item in raw_products:
        item["price"] = clean_price(item.get("price"))
        item["amount_sold_count"] = extract_sold_count(item.get("amount_sold"))

    return raw_products


async def scrape_single_page(browser: Browser, url: str, retries: int = Config.MAX_RETRIES) -> List[Dict]:
    """
    Fetch and parse a single category page using Bright Data,
    with exponential backoff, debug HTML save, and capped retries.
    """
    for attempt in range(1, retries + 1):
        try:
            logger.info(f"🌐 [Page Fetch Attempt {attempt}/{retries}] {url}")

            html = fetch_via_brightdata(url)
            if not html or "<html" not in html:
                raise RuntimeError("Empty or invalid HTML response from Bright Data")

            # Debug save for inspection (optional)
            if attempt == 1:
                with open("last_fetched_page.html", "w", encoding="utf-8") as f:
                    f.write(html)

            # Setup Playwright context
            context = await browser.new_context(
                viewport=Config.VIEWPORT,
                user_agent=Config.USER_AGENT,
            )
            page = await context.new_page()
            await page.goto("about:blank")
            await page.set_content(html, wait_until="domcontentloaded")

            selector = 'a[href*=".html"][href*="/item/"]'
            try:
                await page.wait_for_selector(selector, timeout=DEFAULT_TIMEOUT)
            except Exception:
                logger.warning(f"⚠️ No product links found for {url}. Saving debug HTML...")
                with open("debug_failed_page.html", "w", encoding="utf-8") as f:
                    f.write(html)
                raise RuntimeError("No valid product selector found on page.")

            # Simulated scrolling (helps lazy-loaded DOM)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            await random_delay(Config.BASE_DELAY, *Config.RANDOM_DELAY_RANGE)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await random_delay(Config.BASE_DELAY, *Config.RANDOM_DELAY_RANGE)

            products = await parse_products_from_page(page)
            await context.close()

            logger.info(f"✅ Parsed {len(products)} products from {url}")
            return products

        except Exception as e:
            delay = Config.calculate_retry_delay(attempt)
            if attempt < retries:
                logger.warning(
                    f"⚠️ Error scraping page (attempt {attempt}/{retries}): {e}\n"
                    f"🔁 Retrying in {delay:.2f}s..."
                )
                await asyncio.sleep(delay)
            else:
                logger.error(f"❌ Max retries reached for {url}: {e}")
                return []


async def scrape_pages(
    start_url: str = Config.START_URL,
    pages: int = Config.TOTAL_PAGES,
    concurrency: int = Config.CONCURRENCY_LIMIT,
    output_file: str = Config.OUTPUT_FILE,
):
    """Main scraper routine for multiple pages with concurrency, NDJSON output, and tqdm progress bar."""
    semaphore = asyncio.Semaphore(concurrency)
    seen_urls = set()

    # Load existing URLs to avoid duplicates
    try:
        with open(output_file, "r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    obj = json.loads(line.strip())
                    if obj.get("product_url"):
                        seen_urls.add(obj["product_url"])
                except Exception:
                    continue
    except FileNotFoundError:
        pass

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=Config.HEADLESS)

        async def worker(page_num: int):
            page_url = with_page_param(start_url, page_num)
            async with semaphore:
                await random_delay(Config.BASE_DELAY, *Config.RANDOM_DELAY_RANGE)
                products = await scrape_single_page(browser, page_url)

                new_items = [
                    item for item in products
                    if item.get("product_url") and item["product_url"] not in seen_urls
                ]

                for it in new_items:
                    seen_urls.add(it["product_url"])

                if new_items:
                    with open(output_file, "a", encoding="utf-8") as out:
                        for it in new_items:
                            out.write(json.dumps(it, ensure_ascii=False) + "\n")

                logger.info(f"📦 Page {page_num}: saved {len(new_items)} new products")
                return len(new_items)

        logger.info(f"🚀 Starting scrape for {pages} pages (concurrency={concurrency})...")

        results = await tqdm_asyncio.gather(
            *[worker(i) for i in range(1, pages + 1)],
            desc="Scraping Progress",
            total=pages,
        )

        total_new = sum(r for r in results if isinstance(r, int))
        logger.info(f"🏁 Finished scraping {pages} pages. Total new: {total_new}")

        await browser.close()
    return total_new


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AliExpress Category Scraper")
    parser.add_argument("--pages", type=int, default=Config.TOTAL_PAGES, help="Number of pages to scrape")
    parser.add_argument("--concurrency", type=int, default=Config.CONCURRENCY_LIMIT, help="Concurrent requests")
    parser.add_argument("--output", type=str, default=Config.OUTPUT_FILE, help="NDJSON output file path")
    parser.add_argument("--start-url", type=str, default=Config.START_URL, help="Category start URL")

    args = parser.parse_args()
    asyncio.run(
        scrape_pages(
            start_url=args.start_url,
            pages=args.pages,
            concurrency=args.concurrency,
            output_file=args.output,
        )
    )
