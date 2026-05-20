"""Generate a 1200x630 OG/Twitter share image and a 32x32 + 180x180 favicon set.

Output:
  docs/og-image.png          — 1200x630 social-share card
  docs/favicon.ico           — 32x32 favicon (PNG-in-ICO container)
  docs/apple-touch-icon.png  — 180x180 iOS home-screen icon
  docs/favicon-32.png        — 32x32 fallback PNG

Simple design: navy background, white wordmark, subtitle.
No external dependencies beyond Pillow (already installed).
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

DOCS = Path(__file__).resolve().parents[2] / "docs"
DOCS.mkdir(exist_ok=True)

NAVY = (15, 23, 42)
BLUE = (29, 78, 216)
WHITE = (255, 255, 255)
LIGHT = (203, 213, 225)


def try_font(name: str, size: int):
    """Try system fonts then fall back to default."""
    candidates = [
        f"C:/Windows/Fonts/{name}",
        f"/Library/Fonts/{name}",
        f"/usr/share/fonts/truetype/dejavu/{name}",
        name,
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def render_og_image():
    """1200x630 — Twitter summary_large_image + FB/LinkedIn default size."""
    w, h = 1200, 630
    img = Image.new("RGB", (w, h), NAVY)
    draw = ImageDraw.Draw(img)

    # Left accent bar
    draw.rectangle([(0, 0), (12, h)], fill=BLUE)

    title_font = try_font("seguibl.ttf", 84)  # Segoe UI Black
    if isinstance(title_font, ImageFont.ImageFont):
        title_font = try_font("arialbd.ttf", 84)
    sub_font = try_font("segoeui.ttf", 32)
    foot_font = try_font("segoeui.ttf", 22)

    # Wordmark
    draw.text((80, 180), "FDD Database", fill=WHITE, font=title_font)
    draw.text((80, 300),
              "Franchise costs & earnings,\nside by side.",
              fill=LIGHT, font=sub_font)

    # Stats line + footer
    draw.text((80, 510),
              "Initial fees · Royalties · Total investment · Item 19 earnings",
              fill=LIGHT, font=foot_font)
    draw.text((80, 550),
              "Extracted from publicly filed FDDs.",
              fill=LIGHT, font=foot_font)

    out = DOCS / "og-image.png"
    img.save(out, "PNG", optimize=True)
    print(f"  wrote {out}  ({out.stat().st_size//1024} KB)")


def render_favicons():
    # Simple "FD" wordmark on navy. 512×512 source for sharp downscaling.
    src_size = 512
    img = Image.new("RGB", (src_size, src_size), NAVY)
    draw = ImageDraw.Draw(img)
    # Blue corner accent
    draw.rectangle([(0, 0), (60, src_size)], fill=BLUE)
    font = try_font("seguibl.ttf", 280)
    if isinstance(font, ImageFont.ImageFont):
        font = try_font("arialbd.ttf", 280)
    # Center FD text
    text = "FD"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((src_size - tw) // 2 + 30, (src_size - th) // 2 - 30), text, fill=WHITE, font=font)

    # 180×180 apple-touch
    apple = img.resize((180, 180), Image.LANCZOS)
    apple.save(DOCS / "apple-touch-icon.png", "PNG", optimize=True)
    print(f"  wrote {DOCS/'apple-touch-icon.png'}")

    # 32×32 PNG + ICO
    fav = img.resize((32, 32), Image.LANCZOS)
    fav.save(DOCS / "favicon-32.png", "PNG", optimize=True)
    fav.save(DOCS / "favicon.ico", "ICO", sizes=[(32, 32), (16, 16)])
    print(f"  wrote {DOCS/'favicon.ico'}")
    print(f"  wrote {DOCS/'favicon-32.png'}")


if __name__ == "__main__":
    print("Generating brand image assets...")
    render_og_image()
    render_favicons()
    print("Done.")
