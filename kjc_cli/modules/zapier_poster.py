import requests
from kjc_cli import config
from kjc_cli.logger import get_logger
from tenacity import retry, wait_exponential, stop_after_attempt
import os
import time

logger = get_logger("zapier_poster")

# Map Threads profile IDs to their corresponding Zapier webhook URLs
THREADS_WEBHOOKS = {
    "THREADS_ID_1": "YOUR_ZAPIER_WEBHOOK_URL_1",
    "THREADS_ID_2": "YOUR_ZAPIER_WEBHOOK_URL_2",
    # Add more Threads IDs and webhook URLs as needed
}

def create_product_reply_text(product):
    """Create formatted text for product reply"""
    return f"🛍️ {product['title']}\n💵 {product['price']}\n🔗 {product['link']}"

@retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
def post_to_zapier(webhook_url, text, image_urls=None, product=None):
    """
    Post to Threads via Zapier webhook.
    image_urls: List of publicly accessible image URLs
    product: Product info for reply (if needed)
    """
    payload = {"text": text}
    if image_urls:
        payload["image_urls"] = image_urls
    if product:
        payload["product"] = product

    try:
        response = requests.post(webhook_url, json=payload, timeout=20)
        response.raise_for_status()
        logger.info(f"Successfully posted to Zapier: {response.text}")
        return response.json()
    except Exception as e:
        logger.error(f"Failed to post to Zapier: {str(e)}")
        raise

@retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
def post_to_threads_with_reply(post, threads_id):
    """
    Post to a specific Threads ID via Zapier webhook, including product reply if needed.
    """
    webhook_url = THREADS_WEBHOOKS.get(threads_id)
    if not webhook_url:
        raise ValueError(f"No webhook URL configured for Threads ID: {threads_id}")

    text = post["text"]
    image_urls = post.get("image_urls")  # Expects list of URLs
    product = post.get("product")

    # Include product reply in the main post text (or handle separately in Zapier)
    if product:
        reply_text = create_product_reply_text(product)
        text += f"\n\n{reply_text}"

    return post_to_zapier(webhook_url, text, image_urls, product)

def run_post_many(posts, threads_id):
    """
    Post to a specific Threads ID.
    posts: List of posts (each with text, image_urls, and product)
    threads_id: Target Threads profile ID
    """
    logger.info(f"Posting {len(posts)} posts to Threads ID: {threads_id}")
    results = []

    for i, p in enumerate(posts, 1):
        try:
            logger.info(f"Posting {i}/{len(posts)}: {p['text'][:100]}...")
            result = post_to_threads_with_reply(p, threads_id)
            logger.info(f"Posted {i}/{len(posts)} successfully")
            results.append(result)

            # Add a small delay between posts to avoid rate limiting
            if i < len(posts):
                time.sleep(5)

        except Exception as e:
            logger.exception(f"Posting failed for post {i}", exc_info=e)
            results.append({"error": str(e), "post": p})

    success_count = sum(1 for r in results if "error" not in r)
    logger.info(f"Completed: {success_count}/{len(posts)} posts successful for {threads_id}")

    return results

def run_post_many_to_all_threads(posts):
    """
    Post to all configured Threads IDs.
    posts: List of posts (each with text, image_urls, and product)
    """
    all_results = {}
    for threads_id, webhook_url in THREADS_WEBHOOKS.items():
        all_results[threads_id] = run_post_many(posts, threads_id)
    return all_results
