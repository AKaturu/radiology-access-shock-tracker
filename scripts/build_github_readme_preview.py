"""Build the short README animation from reviewed dashboard screenshots."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "docs" / "assets" / "github"
OUTPUT_PATH = ASSET_DIR / "dashboard-walkthrough.gif"
FRAME_SIZE = (1200, 675)
FRAME_DURATION_MS = 3000
SCENES = (
    ("dashboard-overview.png", "Overview"),
    ("county-shocks.png", "County shocks"),
    ("interventions.png", "Intervention ranking"),
    ("readiness-audit.png", "Readiness audit"),
)


def _load_font() -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    return ImageFont.load_default(size=22)


def _captioned_frame(path: Path, caption: str) -> Image.Image:
    if not path.is_file():
        raise FileNotFoundError(f"Required reviewed screenshot is missing: {path}")

    with Image.open(path) as source:
        contained = ImageOps.contain(
            source.convert("RGB"), FRAME_SIZE, method=Image.Resampling.LANCZOS
        )

    frame = Image.new("RGB", FRAME_SIZE, (245, 247, 250))
    offset = ((frame.width - contained.width) // 2, (frame.height - contained.height) // 2)
    frame.paste(contained, offset)

    draw = ImageDraw.Draw(frame)
    font = _load_font()
    padding = 12
    left, top, right, bottom = draw.textbbox((0, 0), caption, font=font)
    width = right - left
    height = bottom - top
    box = (padding, padding, padding + width + 2 * padding, padding + height + 2 * padding)
    draw.rounded_rectangle(box, radius=6, fill=(19, 49, 88))
    draw.text((2 * padding, 2 * padding), caption, font=font, fill=(255, 255, 255))
    return frame


def build_preview() -> Path:
    frames = [_captioned_frame(ASSET_DIR / filename, caption) for filename, caption in SCENES]
    frames[0].save(
        OUTPUT_PATH,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=FRAME_DURATION_MS,
        loop=0,
        optimize=False,
    )
    return OUTPUT_PATH


if __name__ == "__main__":
    print(build_preview())
