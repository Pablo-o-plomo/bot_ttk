from __future__ import annotations

from pathlib import Path

from PIL import Image


class ImageProcessingError(Exception):
    pass


def process_dish_photo(source_path: str, output_path: str) -> str:
    """Try to remove background and place dish on white background."""
    src = Path(source_path)
    dst = Path(output_path)
    dst.parent.mkdir(parents=True, exist_ok=True)

    if not src.exists():
        raise ImageProcessingError("Исходное изображение не найдено.")

    try:
        from rembg import remove

        with src.open("rb") as f:
            removed_bg_bytes = remove(f.read())

        with Image.open(src).convert("RGBA") as original_img:
            size = original_img.size

        from io import BytesIO

        with Image.open(BytesIO(removed_bg_bytes)).convert("RGBA") as fg:
            fg = fg.resize(size)
            white_bg = Image.new("RGBA", size, (255, 255, 255, 255))
            composited = Image.alpha_composite(white_bg, fg)
            composited.convert("RGB").save(dst, format="JPEG", quality=95)

        return str(dst)
    except Exception as exc:  # noqa: BLE001 - graceful fallback required
        raise ImageProcessingError(str(exc)) from exc
