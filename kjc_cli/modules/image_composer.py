from PIL import Image, ImageDraw, ImageFont, ImageOps
from pathlib import Path
import random
import os
from kjc_cli import config
from kjc_cli.logger import get_logger

logger = get_logger("image_composer")

BG_DIR = config.BACKGROUND_DIR
OUT_DIR = config.COMPOSED_DIR
FONT_PATH = config.FONT_PATH
FONT_SIZE = config.FONT_SIZE
W = config.COMPOSED_WIDTH
H = config.COMPOSED_HEIGHT

def _get_backgrounds_sorted():
    """Get all background images sorted by their number"""
    imgs = list(BG_DIR.glob("*"))
    if not imgs:
        raise FileNotFoundError(f"No background images in {BG_DIR}. Add some images or use images.txt.")
    
    # Sort by filename to ensure consistent order
    imgs.sort(key=lambda x: x.name)
    return imgs

def _get_background_by_index(index):
    """Get background by index (for composed_1 use background_1, etc.)"""
    imgs = _get_backgrounds_sorted()
    if index < len(imgs):
        return imgs[index]
    else:
        # If we run out of backgrounds, cycle through them
        return imgs[index % len(imgs)]

def _load_font(size=FONT_SIZE):
    # Fonts that support both English and Japanese
    bilingual_fonts = [
        FONT_PATH,  # User configured font
        # Noto Sans CJK - excellent for English + Japanese
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansJP-Regular.otf",
        # Takao fonts - good Japanese support with English
        "/usr/share/fonts/truetype/takao-gothic/TakaoGothic.ttf",
        "/usr/share/fonts/truetype/takao-mincho/TakaoMincho.ttf",
        # Windows fonts (if applicable)
        "C:/Windows/Fonts/meiryo.ttc",
        "C:/Windows/Fonts/msgothic.ttc",
        # macOS fonts
        "/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc",
    ]
    
    for font_path in bilingual_fonts:
        try:
            if os.path.exists(font_path):
                font = ImageFont.truetype(font_path, size)
                # Test with both English and Japanese characters
                test_text = "Abcテスト"
                try:
                    bbox = font.getbbox(test_text)
                    logger.info(f"Loaded bilingual font: {os.path.basename(font_path)}")
                    return font
                except Exception as test_error:
                    logger.debug(f"Font {font_path} failed test: {test_error}")
                    continue
        except Exception as e:
            logger.debug(f"Could not load font {font_path}: {e}")
            continue
    
    # Fallback to system default
    try:
        logger.warning("No bilingual fonts found, using system default")
        return ImageFont.load_default()
    except Exception:
        logger.error("Failed to load any font")
        raise

def _is_japanese_text(text):
    """Check if text contains Japanese characters"""
    for char in text:
        # Japanese character ranges:
        # Hiragana: 3040-309F, Katakana: 30A0-30FF, Kanji: 4E00-9FFF
        if ('\u3040' <= char <= '\u309F' or  # Hiragana
            '\u30A0' <= char <= '\u30FF' or  # Katakana  
            '\u4E00' <= char <= '\u9FFF'):   # Kanji
            return True
    return False

def _draw_text_centered(img: Image.Image, text: str, font: ImageFont.FreeTypeFont):
    draw = ImageDraw.Draw(img)
    img_width, img_height = img.size
    max_width = int(img_width * 0.65)
    
    # Choose wrapping method based on text content
    if _is_japanese_text(text):
        # Japanese text wrapping (character-based)
        lines = []
        current_line = ""
        for char in text:
            test_line = current_line + char
            if draw.textlength(test_line, font=font) <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = char
        if current_line:
            lines.append(current_line)
        logger.debug("Used Japanese character-based wrapping")
    else:
        # English text wrapping (word-based)
        lines = []
        words = text.split()
        line = ""
        for w in words:
            test = (line + " " + w).strip()
            if draw.textlength(test, font=font) <= max_width:
                line = test
            else:
                lines.append(line)
                line = w
        if line:
            lines.append(line)
        logger.debug("Used English word-based wrapping")
    
    # Calculate line height and positioning (same for both languages)
    line_height_multiplier = 1.4
    bbox = font.getbbox("Hg")
    font_height = bbox[3] - bbox[1]
    line_spacing = int(font_height * (line_height_multiplier - 1))
    
    total_h = len(lines) * font_height + (len(lines) - 1) * line_spacing
    y_start = int((img_height - total_h) / 2)
    
    # Calculate maximum line width for background rectangle
    max_line_width = 0
    for l in lines:
        line_width = draw.textlength(l, font=font)
        if line_width > max_line_width:
            max_line_width = line_width
    
    # Add padding and draw background
    padding_x = 30
    padding_y = 20
    rect_width = int(max_line_width + (2 * padding_x))
    rect_height = int(total_h + (2 * padding_y))
    
    rect_x = int((img_width - rect_width) / 2)
    rect_y = y_start - padding_y
    
    background = Image.new('RGBA', (rect_width, rect_height), (24, 24, 22, 128))
    img.paste(background, (rect_x, rect_y), background)
    
    # Draw text
    y = y_start
    for l in lines:
        w_text = draw.textlength(l, font=font)
        x = int((img_width - w_text) / 2)
        draw.text((x, y), l, fill=(255, 255, 255, 255), font=font)
        y += font_height + line_spacing

def compose_image(bg_path: Path, hook_text: str, overlays: list = None, output_path: Path = None):
    overlays = overlays or []
    output_path = output_path or (OUT_DIR / (bg_path.stem + "_composed.png"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    
    with Image.open(bg_path) as im:
        # Convert to RGB if needed (for JPEG compatibility)
        if im.mode != 'RGB':
            im = im.convert('RGB')
        
        # Get original dimensions
        orig_width, orig_height = im.size
        
        # Only resize if the image is smaller than target, or use original resolution
        if orig_width < W or orig_height < H:
            # Resize to at least target size while maintaining aspect ratio
            im = ImageOps.fit(im, (W, H), Image.LANCZOS)
            logger.info(f"Upscaled image from {orig_width}x{orig_height} to {W}x{H}")
        else:
            # Use original resolution if it's already high enough
            logger.info(f"Using original resolution: {orig_width}x{orig_height}")
        
        # Convert to RGBA for text overlay
        im = im.convert("RGBA")
        
        font = _load_font()
        _draw_text_centered(im, hook_text, font)
        
        # paste overlays if any (centered)
        for ov in overlays:
            try:
                with Image.open(ov).convert("RGBA") as o:
                    img_width, img_height = im.size
                    o = o.resize((int(img_width*0.25), int(img_height*0.25)))
                    im.paste(o, (int(img_width*0.65), int(img_height*0.65)), o)
            except Exception as e:
                logger.warning(f"Failed to apply overlay {ov}: {e}")
        
        # Save with high quality
        im.save(output_path, quality=95, optimize=True)
    
    logger.info(f"Saved composed image {output_path}")
    return output_path

def run_compose(hooks: list):
    """
    Compose images for each hook. Uses background_1 for composed_1, background_2 for composed_2, etc.
    Returns list of composed image paths.
    """
    logger.info("Starting image composition for hooks")
    composed = []
    
    # Get all available backgrounds sorted
    backgrounds = _get_backgrounds_sorted()
    logger.info(f"Found {len(backgrounds)} background images")
    
    for i, hook in enumerate(hooks):
        try:
            # Use background corresponding to the hook index
            bg = _get_background_by_index(i)
            out = OUT_DIR / f"composed_{i+1}.png"
            
            logger.info(f"Using {bg.name} for composed_{i+1}.png")
            p = compose_image(bg, hook, overlays=[], output_path=out)
            composed.append(str(p))
        except Exception as e:
            logger.exception("Failed to compose image for hook: %s", hook)
    
    return composed