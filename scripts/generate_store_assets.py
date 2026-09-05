#!/usr/bin/env python3
"""Generate launcher icons, PWA icons, and Play Store graphics."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
NAVY = (11, 18, 34, 255)
NAVY_DEEP = (8, 14, 28, 255)
GREEN = (34, 197, 94, 255)
GREEN_DARK = (22, 163, 74, 255)
WHITE = (248, 250, 252, 255)
SOFT = (226, 232, 240, 255)
MUTED = (148, 163, 184, 255)


def _font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf" if bold else "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _rounded_rect(draw: ImageDraw.ImageDraw, box, radius: int, fill) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def _draw_mark(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int) -> None:
    """Leaf-like dumbbell mark used on the launcher icon."""
    r = size // 2
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=GREEN)
    inner = int(r * 0.78)
    draw.ellipse((cx - inner, cy - inner, cx + inner, cy + inner), fill=GREEN_DARK)
    bar_w = max(2, int(size * 0.42))
    bar_h = max(2, int(size * 0.12))
    draw.rounded_rectangle(
        (cx - bar_w, cy - bar_h // 2, cx + bar_w, cy + bar_h // 2),
        radius=bar_h // 2,
        fill=WHITE,
    )
    plate_w = max(3, int(size * 0.14))
    plate_h = max(6, int(size * 0.42))
    for sign in (-1, 1):
        x = cx + sign * bar_w
        draw.rounded_rectangle(
            (x - plate_w // 2, cy - plate_h // 2, x + plate_w // 2, cy + plate_h // 2),
            radius=plate_w // 2,
            fill=WHITE,
        )


def make_launcher(size: int, rounded: bool = False) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pad = int(size * 0.08)
    if rounded:
        _rounded_rect(draw, (pad, pad, size - pad, size - pad), int(size * 0.22), NAVY)
    else:
        draw.rectangle((0, 0, size, size), fill=NAVY)
    _draw_mark(draw, size // 2, int(size * 0.42), int(size * 0.46))
    font = _font(max(12, int(size * 0.22)))
    text = "DF"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((size - tw) / 2, size * 0.68), text, font=font, fill=WHITE)
    return img


def make_adaptive_foreground(size: int = 1080) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    _draw_mark(draw, size // 2, int(size * 0.46), int(size * 0.42))
    font = _font(int(size * 0.16))
    text = "DF"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(((size - tw) / 2, size * 0.70), text, font=font, fill=WHITE)
    return img


def make_play_icon() -> Image.Image:
    return make_launcher(512, rounded=True)


def make_feature_graphic() -> Image.Image:
    w, h = 1024, 500
    img = Image.new("RGBA", (w, h), NAVY_DEEP)
    draw = ImageDraw.Draw(img)
    draw.ellipse((-120, -180, 360, 300), fill=(34, 197, 94, 40))
    draw.ellipse((680, 80, 1180, 620), fill=(56, 189, 248, 28))
    _draw_mark(draw, 180, 250, 210)
    title_font = _font(72)
    sub_font = _font(28, bold=False)
    urdu_font = _font(36)
    draw.text((320, 150), "Desi Fitness", font=title_font, fill=WHITE)
    draw.text((320, 240), "دیسی فٹنس", font=urdu_font, fill=GREEN)
    draw.text((320, 310), "Track desi meals, calories, weight & fasting", font=sub_font, fill=SOFT)
    return img.convert("RGB")


def save_png(img: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG", optimize=True)


def main() -> None:
    android_res = ROOT / "android" / "app" / "src" / "main" / "res"
    densities = {
        "mipmap-mdpi": 48,
        "mipmap-hdpi": 72,
        "mipmap-xhdpi": 96,
        "mipmap-xxhdpi": 144,
        "mipmap-xxxhdpi": 192,
    }
    for folder, size in densities.items():
        icon = make_launcher(size, rounded=False)
        round_icon = make_launcher(size, rounded=True)
        save_png(icon, android_res / folder / "ic_launcher.png")
        save_png(round_icon, android_res / folder / "ic_launcher_round.png")

    fg = make_adaptive_foreground(432)
    save_png(fg, android_res / "drawable-xxhdpi" / "ic_launcher_foreground.png")
    bg = Image.new("RGBA", (432, 432), NAVY)
    save_png(bg, android_res / "drawable-xxhdpi" / "ic_launcher_background.png")

    play = ROOT / "play" / "assets"
    save_png(make_play_icon(), play / "icon_512.png")
    feature = make_feature_graphic()
    play.mkdir(parents=True, exist_ok=True)
    feature.save(play / "feature_graphic_1024x500.png", "PNG", optimize=True)

    static = ROOT / "static"
    save_png(make_launcher(192, rounded=True), static / "icon-192.png")
    save_png(make_launcher(512, rounded=True), static / "icon-512.png")
    save_png(make_launcher(32, rounded=True), static / "favicon.png")
    print("Generated launcher, PWA, and Play Store assets.")


if __name__ == "__main__":
    main()
