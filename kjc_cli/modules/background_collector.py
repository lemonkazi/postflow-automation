import asyncio
import aiohttp
import os
from pathlib import Path
from tenacity import retry, wait_exponential, stop_after_attempt
from kjc_cli import config
from kjc_cli.logger import get_logger

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

@retry(wait=wait_exponential(min=2, max=30), stop=stop_after_attempt(5))  # Increased retries and wait times
async def _fetch(session, url, dest_path: Path):
    timeout = aiohttp.ClientTimeout(total=60)  # Increased to 60s for larger files/network latency
    async with session.get(url, timeout=timeout) as resp:
        if resp.status != 200:
            raise Exception(f"Failed to fetch {url}, status {resp.status}")
        # Stream the response to handle large files without loading into memory
        with open(dest_path, 'wb') as f:
            async for chunk in resp.content.iter_chunked(8192):
                f.write(chunk)
        logger.info(f"Saved {url} -> {dest_path}")

async def _run_download(urls, dest_dir):
    dest_dir.mkdir(parents=True, exist_ok=True)
    connector = aiohttp.TCPConnector(limit=10, limit_per_host=5, ttl_dns_cache=300)  # Optimize connections
    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks = []
        semaphore = asyncio.Semaphore(3)  # Limit concurrent downloads to avoid overwhelming the network/API
        async def _bounded_fetch(url, dest):
            async with semaphore:
                return await _fetch(session, url, dest)
        
        for i, u in enumerate(urls):
            name = f"background_{i+1}.jpg"
            dest = dest_dir / name
            tasks.append(_bounded_fetch(u.strip(), dest))
        await asyncio.gather(*tasks, return_exceptions=True)  # Allow partial failures

async def _search_unsplash(keyword, max_images=5):
    """Search for image URLs from Unsplash API for a given keyword."""
    # Use config key; remove hardcoded for security (set via env/config)
    #key_value = "5HtyzN2tSCkLau7owNQIP8JCWkGykgzQ8SS-08u_gMk"
    key_value = os.getenv("UNSPLASH_ACCESS_KEY", "")
    if not key_value:
        logger.warning(f"No Unsplash access key configured for {keyword}. Skipping.")
        return []
    
    logger.debug(f"Using Unsplash access key (length: {len(key_value)})")
    
    url = f"https://api.unsplash.com/search/photos"
    params = {
        'query': keyword,
        'per_page': max_images,
        'orientation': 'landscape'  # Suitable for backgrounds
    }
    headers = {
        "Authorization": f"Client-ID {key_value}"
    }
    api_timeout = aiohttp.ClientTimeout(total=20)  # Shorter for API calls
    async with aiohttp.ClientSession(timeout=api_timeout) as session:
        async with session.get(url, params=params, headers=headers) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                logger.warning(f"Failed to fetch Unsplash for {keyword}: status {resp.status}, error: {error_text[:200]}")
                return []
            json_data = await resp.json()
            # Use 'regular' for ~1080px resolution (faster download, still high quality for backgrounds)
            image_urls = [photo['urls']['regular'] for photo in json_data.get('results', []) if photo.get('urls')]
            logger.info(f"Found {len(image_urls)} images for keyword '{keyword}'")
            return image_urls

async def _search_images():
    """Search images from Unsplash for all keywords."""
    all_urls = []
    semaphore = asyncio.Semaphore(2)  # Limit concurrent API calls to respect rate limits (50/hour for demo keys)
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
    logger.info(f"Total unique image URLs collected: {len(all_urls)}")
    return all_urls

def run_collect():
    """
    Collects UGC-style background images using Unsplash API:
    1. Searches Unsplash for high-resolution landscape images.
    2. Falls back to images.txt if no URLs are found.
    """
    logger.info("Starting background image collection via Unsplash API")
    urls = asyncio.run(_search_images())

    if not urls and IMAGES_LIST_FILE.exists():
        with open(IMAGES_LIST_FILE, "r", encoding="utf-8") as fh:
            urls = [l.strip() for l in fh if l.strip()]

    if not urls:
        logger.warning("No image URLs found — skipping download. Place image files in data/backgrounds/ manually.")
        return

    asyncio.run(_run_download(urls, DEFAULT_DIR))
    logger.info(f"Download complete. Check {DEFAULT_DIR} for {len(urls)} images.")

if __name__ == "__main__":
    run_collect()