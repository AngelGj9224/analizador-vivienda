"""
Busca en Inmuebles24 todas las zonas configuradas en src/searches.py
(actualmente: casas en San Mateo Atenco, casas en Metepec, y
departamentos en Benito Juárez CDMX) y guarda los resultados nuevos en la
base de datos (data/listings.db). No manda nada por WhatsApp ni corre en
bucle: se ejecuta una sola vez, cada vez que tú lo mandas llamar.

    python -m src.main

Para ver el detalle de lo que se ha ido guardando, abre el panel:

    python -m src.dashboard
"""

import logging

from . import config
from .analysis import compare_listing, compute_market_stats
from .scrapers import inmuebles24
from .searches import SEARCHES
from .storage import Storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("analizador_vivienda")


def format_price(price, currency) -> str:
    if price is None:
        return "Precio no publicado"
    symbol = "$" if currency == "MN" else f"{currency} " if currency else ""
    return f"{symbol}{price:,.0f}".strip()


def run_search(storage: Storage, search: dict):
    logger.info("Buscando: %s...", search["label"])

    listings, reported_total = inmuebles24.scrape(
        slug=search["slug"],
        search_key=search["key"],
        search_label=search["label"],
        max_pages=config.MAX_PAGES,
        headless=config.SCRAPER_HEADLESS,
    )
    logger.info("  %d publicaciones activas encontradas.", len(listings))

    if not listings:
        logger.warning(
            "  No se obtuvo ninguna publicación para esta zona. Si esto se repite, "
            "revisa SCRAPER_HEADLESS=false en .env por si el sitio está bloqueando "
            "el navegador headless."
        )
        return

    new_ids = storage.upsert_listings(listings)
    logger.info("  %d publicaciones nuevas guardadas (el resto ya se conocían).", len(new_ids))

    # Solo damos de baja lo que "desapareció" si la búsqueda de verdad
    # cubrió (más o menos) todo lo que el sitio dice tener para esta zona.
    # Si por un bloqueo parcial solo alcanzamos a leer una fracción de las
    # páginas, no queremos borrar publicaciones válidas por error (esto es
    # normal y esperado en zonas grandes como Metepec o Benito Juárez, que
    # tienen muchas más publicaciones que las que se revisan por corrida).
    current_ids = {l.id for l in listings}
    unique_found = len(current_ids)
    if reported_total and unique_found < reported_total * 0.85:
        logger.info(
            "  Solo se leyeron %d de las %d publicaciones que reporta el sitio para esta "
            "zona; no se dio de baja nada esta vez.",
            unique_found,
            reported_total,
        )
    else:
        removed = storage.deactivate_missing(current_ids, source="inmuebles24", search_key=search["key"])
        if removed:
            logger.info("  %d publicaciones ya no están disponibles y se quitaron del panel.", removed)

    if new_ids:
        zone_listings = [l for l in storage.get_active_listings() if l.search_key == search["key"]]
        stats = compute_market_stats(zone_listings)
        for listing_id in new_ids:
            record = storage.get_by_id(listing_id)
            if record is None:
                continue
            comparison = compare_listing(record, stats)
            logger.info(
                "  Nueva: %s | %s | %s",
                (record.title or "(sin título)")[:70],
                format_price(record.price, record.currency),
                comparison["verdict"],
            )


def run():
    storage = Storage()
    try:
        for search in SEARCHES:
            run_search(storage, search)
        logger.info("Listo. Abre el panel para ver el detalle: python -m src.dashboard")
    finally:
        storage.close()


if __name__ == "__main__":
    run()
