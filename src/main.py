"""
Busca casas en venta en San Mateo Atenco y guarda los resultados nuevos en
la base de datos (data/listings.db). No manda nada por WhatsApp ni corre
en bucle: se ejecuta una sola vez, cada vez que tú lo mandas llamar.

    python -m src.main

Para ver el detalle de lo que se ha ido guardando, abre el panel:

    python -m src.dashboard
"""

import logging

from . import config
from .analysis import compare_listing, compute_market_stats
from .scrapers import inmuebles24
from .storage import Storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("analizador_vivienda")


def format_price(price, currency) -> str:
    if price is None:
        return "Precio no publicado"
    symbol = "$" if currency == "MN" else f"{currency} " if currency else ""
    return f"{symbol}{price:,.0f}".strip()


def run():
    storage = Storage()
    try:
        logger.info("Buscando publicaciones de casas en venta en %s...", config.CIUDAD)

        listings, reported_total = inmuebles24.scrape(
            max_pages=config.MAX_PAGES, headless=config.SCRAPER_HEADLESS
        )
        logger.info("Se encontraron %d publicaciones activas en Inmuebles24.", len(listings))

        if not listings:
            logger.warning(
                "No se obtuvo ninguna publicación. Si esto se repite, revisa "
                "SCRAPER_HEADLESS=false en .env por si el sitio está bloqueando "
                "el navegador headless."
            )
            return

        new_ids = storage.upsert_listings(listings)
        logger.info("%d publicaciones nuevas guardadas (el resto ya se conocían).", len(new_ids))

        # Solo damos de baja lo que "desapareció" si la búsqueda de verdad
        # cubrió (más o menos) todo lo que el sitio dice tener. Si por un
        # bloqueo parcial solo alcanzamos a leer la mitad de las páginas, no
        # queremos borrar publicaciones válidas por error.
        current_ids = {l.id for l in listings}
        unique_found = len(current_ids)
        if reported_total and unique_found < reported_total * 0.85:
            logger.warning(
                "Solo se leyeron %d publicaciones de las %d que reporta el sitio; "
                "por seguridad NO se dio de baja nada esta vez (pudo ser un bloqueo parcial).",
                unique_found,
                reported_total,
            )
        else:
            removed = storage.deactivate_missing(current_ids, source="inmuebles24")
            if removed:
                logger.info("%d publicaciones ya no están disponibles y se quitaron del panel.", removed)

        if new_ids:
            all_active = storage.get_active_listings()
            stats = compute_market_stats(all_active)
            for listing_id in new_ids:
                record = storage.get_by_id(listing_id)
                if record is None:
                    continue
                comparison = compare_listing(record, stats)
                logger.info(
                    "Nueva: %s | %s | %s",
                    (record.title or "(sin título)")[:70],
                    format_price(record.price, record.currency),
                    comparison["verdict"],
                )

        logger.info("Listo. Abre el panel para ver el detalle: python -m src.dashboard")
    finally:
        storage.close()


if __name__ == "__main__":
    run()
