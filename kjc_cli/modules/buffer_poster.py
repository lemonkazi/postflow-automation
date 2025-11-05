import requests
from kjc_cli import config
from kjc_cli.logger import get_logger
from tenacity import retry, wait_exponential, stop_after_attempt
import os
import time

logger = get_logger("buffer_poster")
TOKEN = config.BUFFER_ACCESS_TOKEN
BUFFER_CREATE_URL = "https://api.buffer.com/1/updates/create.json"
BUFFER_UPLOAD_URL = "https://api.buffer.com/1/media/upload.json"

# Add your Threads profile ID here
THREADS_PROFILE_ID = "YOUR_THREADS_PROFILE_ID"  # Replace with your actual profile ID

@retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
def upload_media_to_buffer(image_path):
    """Upload media to Buffer and return media ID"""
    if not TOKEN:
        logger.warning("BUFFER_ACCESS_TOKEN not set — skipping media upload.")
        return None
        
    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    # Check if file exists
    if not os.path.exists(image_path):
        logger.error(f"Image file not found: {image_path}")
        return None
    
    try:
        with open(image_path, 'rb') as image_file:
            files = {'media': (os.path.basename(image_path), image_file)}
            response = requests.post(BUFFER_UPLOAD_URL, headers=headers, files=files, timeout=30)
        
        response.raise_for_status()
        media_data = response.json()
        logger.info(f"Successfully uploaded media: {media_data.get('id')}")
        return media_data['id']
    
    except Exception as e:
        logger.error(f"Failed to upload media {image_path}: {str(e)}")
        raise

def create_product_reply_text(product):
    """Create formatted text for product reply"""
    return f"🛍️ {product['title']}\n💵 {product['price']}\n🔗 {product['link']}"

@retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
def create_buffer_post(text, media_id=None, reply_to_id=None):
    """Generic function to create a Buffer post (main post or reply)"""
    if not TOKEN:
        logger.warning("BUFFER_ACCESS_TOKEN not set — skipping actual posting.")
        return {"status": "skipped", "reason": "no-token"}
    
    payload = {
        "text": text,
        "profile_ids": [THREADS_PROFILE_ID],
    }
    
    # Add media if provided
    if media_id:
        payload["media"] = {'photo': media_id}
    
    # Add reply information if provided
    if reply_to_id:
        # Note: Buffer uses 'top_update_id' for Threads replies
        payload["top_update_id"] = reply_to_id
    
    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    try:
        resp = requests.post(BUFFER_CREATE_URL, headers=headers, json=payload, timeout=20)
        resp.raise_for_status()
        result = resp.json()
        return result
    except Exception as e:
        logger.error(f"Failed to create Buffer post: {str(e)}")
        raise

@retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
def post_to_buffer_with_reply(post):
    """
    Create main post and then a reply with product information
    """
    if not TOKEN:
        logger.warning("BUFFER_ACCESS_TOKEN not set — skipping actual posting. Logging payload instead.")
        logger.info(f"Would post: {post['text'][:200]} -- image: {post.get('image_path')}")
        logger.info(f"Would reply with product: {post['product']}")
        return {"status": "skipped", "reason": "no-token", "payload": post}
    
    # Step 1: Upload image for main post
    media_id = None
    if post.get("image_path"):
        logger.info(f"Uploading image: {post['image_path']}")
        media_id = upload_media_to_buffer(post["image_path"])
    
    # Step 2: Create main post
    logger.info("Creating main post")
    main_post_result = create_buffer_post(post["text"], media_id)
    
    if "error" in main_post_result:
        raise Exception(f"Main post failed: {main_post_result['error']}")
    
    main_post_id = main_post_result.get('updates', [main_post_result])[0].get('id')
    logger.info(f"Main post created with ID: {main_post_id}")
    
    # Small delay to ensure main post is processed
    time.sleep(3)
    
    # Step 3: Create product reply
    logger.info("Creating product reply")
    product_reply_text = create_product_reply_text(post["product"])
    reply_result = create_buffer_post(product_reply_text, reply_to_id=main_post_id)
    
    if "error" in reply_result:
        logger.error(f"Reply post failed: {reply_result['error']}")
        # Still return the main post result even if reply fails
        return {
            "main_post": main_post_result,
            "reply_post": {"error": reply_result["error"]}
        }
    
    logger.info(f"Product reply created with ID: {reply_result.get('id')}")
    
    return {
        "main_post": main_post_result,
        "reply_post": reply_result
    }

def run_post_many(posts):
    logger.info(f"Posting {len(posts)} posts with product replies to profile {THREADS_PROFILE_ID}")
    results = []
    
    for i, p in enumerate(posts, 1):
        try:
            logger.info(f"Posting {i}/{len(posts)}: {p['text'][:100]}...")
            result = post_to_buffer_with_reply(p)
            logger.info(f"Posted {i}/{len(posts)} successfully")
            results.append(result)
            
            # Add a small delay between post sets to avoid rate limiting
            if i < len(posts):
                time.sleep(5)  # Increased delay for the two-post sequence
                
        except Exception as e:
            logger.exception(f"Posting failed for post {i}", exc_info=e)
            results.append({"error": str(e), "post": p})
    
    # Summary
    success_count = sum(1 for r in results if "error" not in r)
    logger.info(f"Completed: {success_count}/{len(posts)} posts successful")
    
    return results