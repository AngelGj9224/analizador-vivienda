"""
Genera una versión estática del panel (HTML + JSON, sin necesitar Flask
corriendo) dentro de la carpeta docs/, lista para publicarse en GitHub
Pages. No sube nada a GitHub por sí solo — solo prepara los archivos;
subirlos (git add/commit/push) lo haces tú, o te ayudo a correrlo cuando
me digas.

    python -m src.publish
"""

import json
import logging
import shutil
from pathlib import Path

from .export_data import listings_payload, stats_payload
from .storage import Storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("publish")

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"
TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "dashboard_static.html"
STATIC_DIR = Path(__file__).resolve().parent / "static"
# Archivos compartidos con el panel local que la versión estática también
# necesita (CSS, JS, y la config de Firebase para los favoritos).
SHARED_ASSETS = ["app.css", "app.js", "favorites.js", "firebase_config.js"]


def publish():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    storage = Storage()
    try:
        listings = listings_payload(storage)
        stats = stats_payload(storage)
    finally:
        storage.close()

    (DOCS_DIR / "listings.json").write_text(
        json.dumps(listings, ensure_ascii=False), encoding="utf-8"
    )
    (DOCS_DIR / "stats.json").write_text(
        json.dumps(stats, ensure_ascii=False), encoding="utf-8"
    )

    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    (DOCS_DIR / "index.html").write_text(html, encoding="utf-8")

    for asset in SHARED_ASSETS:
        shutil.copyfile(STATIC_DIR / asset, DOCS_DIR / asset)

    logger.info("Listo: %d publicaciones exportadas a %s", len(listings), DOCS_DIR)
    logger.info(
        "Para que se vea en tu celular, falta subir esto a GitHub "
        "(git add docs/ && git commit && git push) y tener activado "
        "GitHub Pages apuntando a la carpeta docs/."
    )


if __name__ == "__main__":
    publish()
