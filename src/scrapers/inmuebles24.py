"""
Scraper de Inmuebles24 — la lógica de extracción vive en navent_common.py
(Inmuebles24 y Vivanuncios comparten la misma plataforma). Este módulo
solo sabe armar las URLs de búsqueda/paginación propias de Inmuebles24.
"""

from .navent_common import scrape_navent_site

BASE_URL = "https://www.inmuebles24.com"
SOURCE = "inmuebles24"


def _page_url(slug: str, page_num: int) -> str:
    suffix = "" if page_num == 1 else f"-pagina-{page_num}"
    return f"{BASE_URL}/{slug}{suffix}.html"


def scrape(slug: str, search_key: str, search_label: str, max_pages: int = 3, headless: bool = True):
    """Recorre los resultados de Inmuebles24 para la búsqueda `slug`
    (p. ej. "casas-en-venta-en-metepec"), etiquetando cada publicación con
    `search_key`/`search_label` para poder filtrarlas y compararlas por
    separado en el panel. Devuelve (listings, total_reportado_por_el_sitio)."""
    return scrape_navent_site(
        base_url=BASE_URL,
        source=SOURCE,
        page_url_fn=lambda page_num: _page_url(slug, page_num),
        search_key=search_key,
        search_label=search_label,
        max_pages=max_pages,
        headless=headless,
    )
