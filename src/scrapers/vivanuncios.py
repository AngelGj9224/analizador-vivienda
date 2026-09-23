"""
Scraper de Vivanuncios — misma plataforma que Inmuebles24 (mismo HTML,
mismos atributos `data-qa`), así que reutiliza navent_common.py. Este
módulo solo arma las URLs propias de Vivanuncios, que se ven así:

    Página 1:  /s-venta-inmuebles/<slug>/v1c<categoria>l<location_id>p1<query>
    Página N:  /s-venta-inmuebles/<slug>/page-N/v1c<categoria>l<location_id>pN<query>

`slug`, `categoria`, `location_id` y `query` salen de usar el buscador del
sitio (escribir la ubicación, elegir tipo de inmueble, Comprar, Buscar) y
copiar la URL resultante — no hay que adivinarlos.
"""

from .navent_common import scrape_navent_site

BASE_URL = "https://www.vivanuncios.com.mx"
SOURCE = "vivanuncios"


def _page_url(slug: str, category: int, location_id: int, query: str, page_num: int) -> str:
    page_segment = "" if page_num == 1 else f"page-{page_num}/"
    qs = f"?{query}" if query else ""
    return f"{BASE_URL}/s-venta-inmuebles/{slug}/{page_segment}v1c{category}l{location_id}p{page_num}{qs}"


def scrape(
    slug: str,
    category: int,
    location_id: int,
    search_key: str,
    search_label: str,
    query: str = "",
    max_pages: int = 3,
    headless: bool = True,
):
    """Devuelve (listings, total_reportado_por_el_sitio)."""
    return scrape_navent_site(
        base_url=BASE_URL,
        source=SOURCE,
        page_url_fn=lambda page_num: _page_url(slug, category, location_id, query, page_num),
        search_key=search_key,
        search_label=search_label,
        max_pages=max_pages,
        headless=headless,
    )
