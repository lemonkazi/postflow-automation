import asyncio
import aiohttp
import os
from pathlib import Path
from tenacity import retry, wait_exponential, stop_after_attempt
from kjc_cli import config
from kjc_cli.logger import get_logger
import re
from bs4 import BeautifulSoup

logger = get_logger("background_collector")
IMAGES_LIST_FILE = Path("images.txt")  # fallback
DEFAULT_DIR = config.BACKGROUND_DIR

# Keywords for UGC-style background images
KEYWORDS = [
    "convenience store UGC background high resolution",
    "cafe interior HD background",
    "street photography 4K background",
    "laundromat wide angle background",
    "store interior professional photography"
]

@retry(wait=wait_exponential(min=1, max=10), stop=stop_after_attempt(3))
async def _fetch(session, url, dest_path: Path):
    async with session.get(url, timeout=30) as resp:
        if resp.status != 200:
            raise Exception(f"Failed to fetch {url}, status {resp.status}")
        data = await resp.read()
        dest_path.write_bytes(data)
        logger.info(f"Saved {url} -> {dest_path}")

async def _run_download(urls, dest_dir):
    dest_dir.mkdir(parents=True, exist_ok=True)
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i, u in enumerate(urls):
            name = f"background_{i+1}.jpg"
            dest = dest_dir / name
            tasks.append(_fetch(session, u.strip(), dest))
        await asyncio.gather(*tasks)

async def _scrape_google_images(keyword, max_images=5):
    """Scrape image URLs from Google Images for a given keyword."""
    url = f"https://www.google.com/search?q={keyword}&tbm=isch"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                logger.warning(f"Failed to fetch Google Images for {keyword}")
                return []
            html = await resp.text()

            image_urls = []
            # This regex is designed to find the data embedded in the script tags.
            # It's looking for a list where the 1st element is the image URL,
            # the 2nd is the height, and the 3rd is the width.
            # This is fragile and might break if Google changes their markup.
            potential_urls = re.findall(r'\["(https://[^"]+)",(\\d+),(\\d+)\]', html)
            for url, height, width in potential_urls:
                if int(height) > 800 and int(width) > 800: # Filter for larger images
                    image_urls.append(url)
                    if len(image_urls) >= max_images:
                        break
            
            if not image_urls:
                logger.warning("Could not find high-resolution images, falling back to lower-resolution.")
                soup = BeautifulSoup(html, "html.parser")
                for img in soup.find_all("img"):
                    src = img.get("data-src") or img.get("src")
                    if src and src.startswith("http"):
                        image_urls.append(src)
                        if len(image_urls) >= max_images:
                            break

            return image_urls

async def _scrape_pinterest_images(keyword, max_images=5):
    """Scrape image URLs from Pinterest for a given keyword."""
    url = f"https://www.pinterest.com/search/pins/?q={keyword}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                logger.warning(f"Failed to fetch Pinterest for {keyword}")
                return []
            html = await resp.text()
            # Pinterest image URLs are often in meta tags or script tags
            # This regex is a simple approach; you may need to refine it
            image_urls = re.findall(r'"originalUrl":"(https://[^"]+)"', html)
            return list(set(image_urls))[:max_images]

async def _scrape_images():
    """Scrape images from Google and Pinterest for all keywords."""
    all_urls = []
    for keyword in KEYWORDS:
        google_urls = await _scrape_google_images(keyword)
        #pinterest_urls = await _scrape_pinterest_images(keyword)
        all_urls.extend(google_urls)
        #all_urls.extend(pinterest_urls)
    return all_urls

def run_collect():
    """
    Collects UGC-style background images:
    1. Tries to scrape from Google and Pinterest.
    2. Falls back to images.txt if no URLs are found.
    """
    logger.info("Starting background image collection")
    urls = asyncio.run(_scrape_images())

    # if not urls and IMAGES_LIST_FILE.exists():
    #     with open(IMAGES_LIST_FILE, "r", encoding="utf-8") as fh:
    #         urls = [l.strip() for l in fh if l.strip()]

    if not urls:
        logger.warning("No image URLs found — skipping download. Place image files in data/backgrounds/ manually.")
        return

    asyncio.run(_run_download(urls, DEFAULT_DIR))

if __name__ == "__main__":
    run_collect()
