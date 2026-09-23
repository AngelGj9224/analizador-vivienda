"""
Scraper de Inmuebles24, reutilizable para cualquier búsqueda del sitio
(casas, departamentos, distintas ciudades) — ver src/searches.py para la
lista de zonas configuradas.

Los selectores usan los atributos `data-qa` que el propio sitio usa para
sus pruebas automatizadas (más estables que las clases CSS, que cambian
seguido). Si Inmuebles24 rediseña su página y esto deja de funcionar,
hay que volver a inspeccionar el HTML y actualizar los selectores de
abajo.
"""

import logging
import re
from typing import List, Optional

from playwright.sync_api import Page, sync_playwright

from .base import Listing

logger = logging.getLogger(__name__)

BASE_URL = "https://www.inmuebles24.com"
SOURCE = "inmuebles24"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def _parse_price(text: Optional[str]):
    if not text:
        return None, None
    m = re.search(r"(MN|USD)\s*([\d.,]+)", text.strip())
    if not m:
        return None, None
    currency, amount = m.groups()
    try:
        return float(amount.replace(",", "")), currency
    except ValueError:
        return None, None


def _parse_features(text: Optional[str]) -> dict:
    """Texto tipo: '84 m² lote2 rec.2 baños2 estac.'"""
    result = {"lot_size": None, "bedrooms": None, "bathrooms": None, "parking": None}
    if not text:
        return result

    # El número siempre empieza con un dígito (nunca con el punto de la
    # palabra anterior, p. ej. "...rec.2 baños" no debe capturar ".2").
    num = r"(\d+(?:[.,]\d+)?)"

    m = re.search(num + r"\s*m²\s*lote", text)
    if m:
        result["lot_size"] = float(m.group(1).replace(",", ""))

    m = re.search(num + r"\s*rec", text)
    if m:
        result["bedrooms"] = int(float(m.group(1).replace(",", "")))

    m = re.search(num + r"\s*ba[ñn]os?", text)
    if m:
        result["bathrooms"] = float(m.group(1).replace(",", ""))

    m = re.search(num + r"\s*estac", text)
    if m:
        result["parking"] = int(float(m.group(1).replace(",", "")))

    return result


def _text_or_none(card, selector: str) -> Optional[str]:
    el = card.query_selector(selector)
    return el.inner_text() if el else None


def _extract_cards(page: Page, search_key: str, search_label: str) -> List[Listing]:
    cards = page.query_selector_all('div[data-qa="posting PROPERTY"]')
    listings: List[Listing] = []

    for card in cards:
        try:
            post_id = card.get_attribute("data-id")
            rel_url = card.get_attribute("data-to-posting")
            if not post_id or not rel_url:
                continue
            full_url = rel_url if rel_url.startswith("http") else BASE_URL + rel_url.split("?")[0]

            price, currency = _parse_price(_text_or_none(card, '[data-qa="POSTING_CARD_PRICE"]'))
            maintenance, _ = _parse_price(_text_or_none(card, '[data-qa="expensas"]'))
            features = _parse_features(_text_or_none(card, '[data-qa="POSTING_CARD_FEATURES"]'))
            location = (_text_or_none(card, '[data-qa="POSTING_CARD_LOCATION"]') or "").strip()
            title = (_text_or_none(card, '[data-qa="POSTING_CARD_DESCRIPTION"]') or "").strip()

            listings.append(
                Listing(
                    id=f"i24-{post_id}",
                    source=SOURCE,
                    title=title,
                    url=full_url,
                    price=price,
                    currency=currency,
                    maintenance=maintenance,
                    lot_size=features["lot_size"],
                    bedrooms=features["bedrooms"],
                    bathrooms=features["bathrooms"],
                    parking=features["parking"],
                    location=location,
                    search_key=search_key,
                    search_label=search_label,
                )
            )
        except Exception as e:
            logger.warning("No se pudo procesar una tarjeta de Inmuebles24: %s", e)

    return listings


def _page_url(slug: str, page_num: int) -> str:
    suffix = "" if page_num == 1 else f"-pagina-{page_num}"
    return f"{BASE_URL}/{slug}{suffix}.html"


_TITLE_COUNT_RE = re.compile(r"^\s*([\d,]+)\s")


def scrape(slug: str, search_key: str, search_label: str, max_pages: int = 3, headless: bool = True):
    """Recorre los resultados de Inmuebles24 para la búsqueda `slug`
    (p. ej. "casas-en-venta-en-metepec"), etiquetando cada publicación con
    `search_key`/`search_label` para poder filtrarlas y compararlas por
    separado en el panel.

    Importante: Cloudflare (la protección anti-bots del sitio) bloquea la
    sesión en cuanto detecta una SEGUNDA navegación dentro del mismo
    contexto de navegador, sin importar si se hace con un link.click() real,
    con page.goto() directo, o metiendo pausas entre medio: todo se marcó
    como bloqueado en las pruebas. Lo único que sí funciona de forma
    confiable es abrir un navegador nuevo (proceso y huella distintos) para
    cada página de resultados. Por eso aquí se relanza Chromium en cada
    iteración en vez de reutilizar la misma pestaña.

    Devuelve (listings, total_reportado_por_el_sitio). `total_reportado` sale
    del título de la página 1 (p. ej. "77 Casas en venta..."); si no se pudo
    leer, es None. Sirve para que quien llama esta función pueda saber si la
    búsqueda cubrió razonablemente todo lo que el sitio dice tener antes de
    usar el resultado para dar de baja publicaciones que ya no aparecieron.
    """
    all_listings: List[Listing] = []
    reported_total: Optional[int] = None

    with sync_playwright() as p:
        for page_num in range(1, max_pages + 1):
            url = _page_url(slug, page_num)
            browser = p.chromium.launch(headless=headless)
            try:
                context = browser.new_context(user_agent=USER_AGENT, locale="es-MX")
                page = context.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                try:
                    page.wait_for_selector('div[data-qa="posting PROPERTY"]', timeout=20000)
                except Exception:
                    logger.info("Página %d sin resultados (o bloqueada por el sitio).", page_num)
                    break

                if page_num == 1:
                    m = _TITLE_COUNT_RE.match(page.title() or "")
                    if m:
                        try:
                            reported_total = int(m.group(1).replace(",", ""))
                        except ValueError:
                            reported_total = None

                listings = _extract_cards(page, search_key, search_label)
                if not listings:
                    break
                all_listings.extend(listings)
            except Exception as e:
                logger.error("Error obteniendo la página %d de Inmuebles24: %s", page_num, e)
                break
            finally:
                browser.close()
    return all_listings, reported_total
