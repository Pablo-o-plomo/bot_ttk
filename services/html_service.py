from __future__ import annotations

import base64
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import EXPORTS_DIR, TEMPLATES_DIR
from models import Dish


env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def _image_to_data_uri(image_path: str | None) -> str:
    if not image_path:
        return ""

    path = Path(image_path)
    if not path.exists():
        return ""

    mime = "image/jpeg"
    if path.suffix.lower() == ".png":
        mime = "image/png"

    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def generate_dish_html(dish: Dish) -> str:
    image_path = dish.processed_photo_path or dish.photo_path
    template = env.get_template("dish_card.html")
    html = template.render(
        dish=dish,
        generated_at=datetime.now().strftime("%d.%m.%Y %H:%M"),
        image_data_uri=_image_to_data_uri(image_path),
    )

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    safe_title = "".join(ch if ch.isalnum() else "_" for ch in dish.title)[:60] or f"dish_{dish.id}"
    filename = f"dish_card_{dish.id}_{safe_title}.html"
    output_path = EXPORTS_DIR / filename
    output_path.write_text(html, encoding="utf-8")
    return str(output_path)
