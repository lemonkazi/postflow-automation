import asyncio
import aiohttp
import os
import random
from pathlib import Path
from tenacity import retry, wait_exponential, stop_after_attempt
from bs4 import BeautifulSoup
from kjc_cli import config
from kjc_cli.logger import get_logger

logger = get_logger("background_collector")
IMAGES_LIST_FILE = Path("images.txt")
DEFAULT_DIR = config.BACKGROUND_DIR

# Multiple Pinterest boards — add as many as you want
PINTEREST_URLS = [
    "https://www.pinterest.com/kj512ii/girl-street-fashion/"
]
# Keywords for UGC-style background images
KEYWORDS = [
    "convenience store UGC background high resolution",
    "cafe interior HD background",
    "street photography 4K background",
    "laundromat wide angle background",
    "store interior professional photography"
]

@retry(wait=wait_exponential(min=2, max=30), stop=stop_after_attempt(5))
async def _fetch(session, url, dest_path: Path):
    """Download and save image."""
    timeout = aiohttp.ClientTimeout(total=60)
    async with session.get(url, timeout=timeout) as resp:
        if resp.status != 200:
            raise Exception(f"Failed to fetch {url}, status {resp.status}")
        with open(dest_path, 'wb') as f:
            async for chunk in resp.content.iter_chunked(8192):
                f.write(chunk)
        logger.info(f"Saved {url} -> {dest_path}")

async def _run_download(urls, dest_dir):
    """Download all collected image URLs."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    connector = aiohttp.TCPConnector(limit=10, limit_per_host=5, ttl_dns_cache=300)
    timeout = aiohttp.ClientTimeout(total=60)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        semaphore = asyncio.Semaphore(4)
        async def _bounded_fetch(url, dest):
            async with semaphore:
                return await _fetch(session, url, dest)

        tasks = []
        for i, u in enumerate(urls):
            name = f"background_{i+1}.jpg"
            dest = dest_dir / name
            tasks.append(_bounded_fetch(u.strip(), dest))
        await asyncio.gather(*tasks, return_exceptions=True)

async def _search_unsplash(keyword, max_images=5):
    """Search for image URLs from Unsplash API for a given keyword."""
    key_value = os.getenv("UNSPLASH_ACCESS_KEY", "")
    if not key_value:
        logger.warning(f"No Unsplash access key configured for {keyword}. Skipping.")
        return []
    
    logger.debug(f"Using Unsplash access key (length: {len(key_value)})")
    
    url = f"https://api.unsplash.com/search/photos"
    params = {
        'query': keyword,
        'per_page': max_images,
        'orientation': 'landscape'
    }
    headers = {
        "Authorization": f"Client-ID {key_value}"
    }
    api_timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=api_timeout) as session:
        async with session.get(url, params=params, headers=headers) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                logger.warning(f"Failed to fetch Unsplash for {keyword}: status {resp.status}, error: {error_text[:200]}")
                return []
            json_data = await resp.json()
            # Use 'raw' for highest quality, fallback to 'full'
            image_urls = []
            for photo in json_data.get('results', []):
                if photo.get('urls'):
                    # Try to get the highest quality available
                    img_url = photo['urls'].get('raw') or photo['urls'].get('full') or photo['urls'].get('regular')
                    if img_url:
                        image_urls.append(img_url)
            logger.info(f"Found {len(image_urls)} high-res images for keyword '{keyword}'")
            return image_urls

async def _search_images():
    """Search images from Unsplash for all keywords."""
    all_urls = []
    semaphore = asyncio.Semaphore(2)
    async def _bounded_search(keyword):
        async with semaphore:
            return await _search_unsplash(keyword)
    
    tasks = [_bounded_search(keyword) for keyword in KEYWORDS]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for unsplash_urls in results:
        if isinstance(unsplash_urls, list):
            all_urls.extend(unsplash_urls)
    # Deduplicate URLs
    all_urls = list(set(all_urls))
    logger.info(f"Total unique high-res image URLs collected: {len(all_urls)}")
    return all_urls

async def _scrape_pinterest_images(board_url, max_images=15):
    """Scrape high-resolution image URLs from a Pinterest board."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/122.0.0.0 Safari/537.36"
    }

    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        async with session.get(board_url) as resp:
            if resp.status != 200:
                logger.warning(f"Failed to fetch Pinterest board ({resp.status}): {board_url}")
                return []
            html = await resp.text()

    soup = BeautifulSoup(html, "html.parser")
    image_urls = []
    
    # Look for high-resolution images in various attributes
    for img in soup.find_all("img"):
        src = img.get("src", "")
        
        # Skip small images and icons
        if not src or "pinimg.com" not in src:
            continue
            
        # Try to get higher resolution by replacing URL patterns
        high_res_url = src
        
        # Replace common Pinterest thumbnail patterns with higher res versions
        if "236x" in src:
            high_res_url = src.replace("236x", "736x")  # Medium size
        elif "140x" in src:
            high_res_url = src.replace("140x", "736x")
        elif "75x" in src:
            high_res_url = src.replace("75x", "736x")
            
        # Also check for data sources that might have higher res
        if img.get("data-src"):
            data_src = img["data-src"]
            if "pinimg.com" in data_src and "736x" in data_src:
                high_res_url = data_src
                
        image_urls.append(high_res_url)

    random.shuffle(image_urls)
    logger.info(f"Found {len(image_urls)} Pinterest images from {board_url}")
    return image_urls[:max_images]

async def _collect_from_all_boards():
    """Run scraping for multiple Pinterest boards concurrently."""
    tasks = [_scrape_pinterest_images(url) for url in PINTEREST_URLS]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    all_urls = []
    for res in results:
        if isinstance(res, list):
            all_urls.extend(res)
    all_urls = list(set(all_urls))

    random.shuffle(all_urls)
    all_urls = all_urls[:20]
    logger.info(f"Collected {len(all_urls)} random Pinterest images.")
    return all_urls

def run_collect():
    """Main entry point for Pinterest-based image collection."""
    logger.info("Starting high-resolution background image collection...")

    # Get images from both sources
    #unsplash_urls = asyncio.run(_search_images())
    pinterest_urls = asyncio.run(_collect_from_all_boards())
    
    # Combine both sources
    #urls = unsplash_urls + pinterest_urls
    urls = pinterest_urls
    
    if not urls and IMAGES_LIST_FILE.exists():
        with open(IMAGES_LIST_FILE, "r", encoding="utf-8") as fh:
            urls = [l.strip() for l in fh if l.strip()]

    if not urls:
        logger.warning("No image URLs found — skipping download.")
        return

    asyncio.run(_run_download(urls, DEFAULT_DIR))
    logger.info(f"Download complete. Check {DEFAULT_DIR} for {len(urls)} high-res images.")

if __name__ == "__main__":
    run_collect()