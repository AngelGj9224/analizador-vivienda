"""
Lógica compartida para sitios de la familia Navent (Inmuebles24,
Vivanuncios, Zonaprop, ...): usan exactamente el mismo HTML con los
mismos atributos `data-qa`, así que un solo scraper genérico sirve para
todos — cada sitio solo aporta su URL base y cómo arma la URL de cada
página de resultados.

Importante (confirmado con pruebas): estos sitios bloquean con
Cloudflare la sesión en cuanto detectan una SEGUNDA navegación dentro
del mismo contexto de navegador (sin importar si es con un click real, un
goto() directo, o con pausas entre medio). Lo único que funciona de forma
confiable es abrir un navegador nuevo para cada página. Por eso
`scrape_navent_site` relanza Chromium en cada iteración.
"""

import logging
import re
from typing import Callable, List, Optional

from playwright.sync_api import Page, sync_playwright

from .base import Listing

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

_TITLE_COUNT_RE = re.compile(r"^\s*([\d,]+)\s")

# El número siempre empieza con un dígito (nunca con el punto de la
# palabra anterior, p. ej. "...rec.2 baños" no debe capturar ".2").
_NUM = r"(\d+(?:[.,]\d+)?)"

_AGE_PATTERNS = [
    re.compile(_NUM + r"\s*años?\s*de\s*antig[üu]edad", re.IGNORECASE),
    re.compile(r"antig[üu]edad[:\s]+" + _NUM + r"\s*años?", re.IGNORECASE),
]


def parse_price(text: Optional[str]):
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


def parse_features(text: Optional[str]) -> dict:
    """Texto tipo: '84 m² lote2 rec.2 baños2 estac.'"""
    result = {"lot_size": None, "bedrooms": None, "bathrooms": None, "parking": None}
    if not text:
        return result

    m = re.search(_NUM + r"\s*m²\s*lote", text)
    if m:
        result["lot_size"] = float(m.group(1).replace(",", ""))

    m = re.search(_NUM + r"\s*rec", text)
    if m:
        result["bedrooms"] = int(float(m.group(1).replace(",", "")))

    m = re.search(_NUM + r"\s*ba[ñn]os?", text)
    if m:
        result["bathrooms"] = float(m.group(1).replace(",", ""))

    m = re.search(_NUM + r"\s*estac", text)
    if m:
        result["parking"] = int(float(m.group(1).replace(",", "")))

    return result


def parse_age_years(text: Optional[str]) -> Optional[int]:
    """Busca frases tipo 'Antigüedad: 25 años' o '11 años de antigüedad'
    en el título/descripción. Muchas publicaciones no lo mencionan, así
    que devuelve None con frecuencia — es un dato "cuando se pueda", no
    algo que el sitio garantice en todas las publicaciones."""
    if not text:
        return None
    for pattern in _AGE_PATTERNS:
        m = pattern.search(text)
        if m:
            try:
                return int(float(m.group(1).replace(",", "")))
            except ValueError:
                continue
    return None


def _text_or_none(card, selector: str) -> Optional[str]:
    el = card.query_selector(selector)
    return el.inner_text() if el else None


def extract_cards(
    page: Page, base_url: str, source: str, search_key: str, search_label: str
) -> List[Listing]:
    cards = page.query_selector_all('div[data-qa="posting PROPERTY"]')
    listings: List[Listing] = []

    for card in cards:
        try:
            post_id = card.get_attribute("data-id")
            rel_url = card.get_attribute("data-to-posting")
            if not post_id or not rel_url:
                continue
            full_url = rel_url if rel_url.startswith("http") else base_url + rel_url.split("?")[0]

            price, currency = parse_price(_text_or_none(card, '[data-qa="POSTING_CARD_PRICE"]'))
            maintenance, _ = parse_price(_text_or_none(card, '[data-qa="expensas"]'))
            features = parse_features(_text_or_none(card, '[data-qa="POSTING_CARD_FEATURES"]'))
            location = (_text_or_none(card, '[data-qa="POSTING_CARD_LOCATION"]') or "").strip()
            title = (_text_or_none(card, '[data-qa="POSTING_CARD_DESCRIPTION"]') or "").strip()
            age_years = parse_age_years(title)

            listings.append(
                Listing(
                    id=f"{source}-{post_id}",
                    source=source,
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
                    age_years=age_years,
                    search_key=search_key,
                    search_label=search_label,
                )
            )
        except Exception as e:
            logger.warning("[%s] No se pudo procesar una tarjeta: %s", source, e)

    return listings


def scrape_navent_site(
    *,
    base_url: str,
    source: str,
    page_url_fn: Callable[[int], str],
    search_key: str,
    search_label: str,
    max_pages: int = 3,
    headless: bool = True,
):
    """Recorre los resultados de un sitio de la familia Navent.

    `page_url_fn(page_num)` arma la URL completa de esa página de
    resultados; cada sitio la implementa distinto (Inmuebles24 usa
    "-pagina-N.html", Vivanuncios usa "/page-N/...").

    Devuelve (listings, total_reportado_por_el_sitio).
    """
    all_listings: List[Listing] = []
    reported_total: Optional[int] = None

    with sync_playwright() as p:
        for page_num in range(1, max_pages + 1):
            url = page_url_fn(page_num)
            browser = p.chromium.launch(headless=headless)
            try:
                context = browser.new_context(user_agent=USER_AGENT, locale="es-MX")
                page = context.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                try:
                    page.wait_for_selector('div[data-qa="posting PROPERTY"]', timeout=20000)
                except Exception:
                    logger.info("[%s] Página %d sin resultados (o bloqueada por el sitio).", source, page_num)
                    break

                if page_num == 1:
                    m = _TITLE_COUNT_RE.match(page.title() or "")
                    if m:
                        try:
                            reported_total = int(m.group(1).replace(",", ""))
                        except ValueError:
                            reported_total = None

                listings = extract_cards(page, base_url, source, search_key, search_label)
                if not listings:
                    break
                all_listings.extend(listings)
            except Exception as e:
                logger.error("[%s] Error obteniendo la página %d: %s", source, page_num, e)
                break
            finally:
                browser.close()
    return all_listings, reported_total
