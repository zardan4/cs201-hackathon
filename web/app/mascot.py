"""Mascot sprites: one image per mood/place, with a safe fallback to the default sprite.

Drop a file named after the sprite into static/mascot/ (png, webp, svg or gif) and it is
picked up automatically; until it exists the default sprite is used. See docs/MASCOT.md.
"""

from pathlib import Path

from flask import current_app, url_for

SPRITE_EXTENSIONS = ("png", "webp", "svg", "gif")
DEFAULT_SPRITE = "default"


def mascot_url(name: str) -> str:
    """URL of the sprite `name`, or of the default sprite if that file does not exist yet."""
    folder = Path(current_app.static_folder) / "mascot"
    for sprite in (name, DEFAULT_SPRITE):
        for extension in SPRITE_EXTENSIONS:
            if (folder / f"{sprite}.{extension}").is_file():
                return url_for("static", filename=f"mascot/{sprite}.{extension}")
    return url_for("static", filename="mascot/default.png")
