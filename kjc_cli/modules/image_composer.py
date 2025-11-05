from PIL import Image, ImageDraw, ImageFont, ImageOps
from pathlib import Path
import random
from kjc_cli import config
from kjc_cli.logger import get_logger

logger = get_logger("image_composer")

BG_DIR = config.BACKGROUND_DIR
OUT_DIR = config.COMPOSED_DIR
FONT_PATH = config.FONT_PATH
FONT_SIZE = config.FONT_SIZE
W = config.COMPOSED_WIDTH
H = config.COMPOSED_HEIGHT

def _choose_background():
    imgs = list(BG_DIR.glob("*"))
    if not imgs:
        raise FileNotFoundError(f"No background images in {BG_DIR}. Add some images or use images.txt.")
    return random.choice(imgs)

def _load_font(size=FONT_SIZE):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except Exception:
        logger.warning("Failed to load specified font; using default")
        return ImageFont.load_default()

def _draw_text_centered(img: Image.Image, text: str, font: ImageFont.FreeTypeFont):
    draw = ImageDraw.Draw(img)
    max_width = int(W * 0.85)
    # naive wrap
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
    total_h = sum([font.getbbox(l)[3] - font.getbbox(l)[1] for l in lines])
    y = int((H - total_h) / 4)
    for l in lines:
        w_text = draw.textlength(l, font=font)
        x = int((W - w_text) / 2)
        draw.text((x, y), l, fill=(255,255,255,255), font=font, stroke_width=2, stroke_fill=(0,0,0))
        y += font.getbbox(l)[3] - font.getbbox(l)[1] + 8

def compose_image(bg_path: Path, hook_text: str, overlays: list = None, output_path: Path = None):
    overlays = overlays or []
    output_path = output_path or (OUT_DIR / (bg_path.stem + "_composed.png"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with Image.open(bg_path) as im:
        im = im.convert("RGBA")
        im = ImageOps.fit(im, (W, H), Image.LANCZOS)
        font = _load_font()
        _draw_text_centered(im, hook_text, font)
        # paste overlays if any (centered)
        for ov in overlays:
            try:
                with Image.open(ov).convert("RGBA") as o:
                    o = o.resize((int(W*0.25), int(H*0.25)))
                    im.paste(o, (int(W*0.65), int(H*0.65)), o)
            except Exception as e:
                logger.warning(f"Failed to apply overlay {ov}: {e}")
        im.save(output_path)
    logger.info(f"Saved composed image {output_path}")
    return output_path

def run_compose(hooks: list):
    """
    Compose images for each hook. If fewer backgrounds than hooks, reuse backgrounds.
    Returns list of composed image paths.
    """
    logger.info("Starting image composition for hooks")
    composed = []
    for i, hook in enumerate(hooks):
        try:
            bg = _choose_background()
            out = OUT_DIR / f"composed_{i+1}.png"
            p = compose_image(bg, hook, overlays=[], output_path=out)
            composed.append(str(p))
        except Exception as e:
            logger.exception("Failed to compose image for hook: %s", hook)
    return composed