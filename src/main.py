"""
Busca, en todas las zonas y fuentes configuradas en src/searches.py
(actualmente: Inmuebles24 y Vivanuncios, para casas en San Mateo Atenco,
casas en Metepec, y departamentos en Benito Juárez CDMX), y guarda los
resultados nuevos en la base de datos (data/listings.db). No manda nada
por WhatsApp ni corre en bucle: se ejecuta una sola vez, cada vez que tú
lo mandas llamar.

    python -m src.main

Para ver el detalle de lo que se ha ido guardando, abre el panel:

    python -m src.dashboard
"""

import logging

from . import config
from .analysis import compare_listing, compute_market_stats
from .scrapers import inmuebles24, vivanuncios
from .searches import ZONES
from .storage import Storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("analizador_vivienda")


def format_price(price, currency) -> str:
    if price is None:
        return "Precio no publicado"
    symbol = "$" if currency == "MN" else f"{currency} " if currency else ""
    return f"{symbol}{price:,.0f}".strip()


def _scrape_source(source_name: str, cfg: dict, zone: dict):
    common = dict(
        search_key=zone["key"],
        search_label=zone["label"],
        max_pages=config.MAX_PAGES,
        headless=config.SCRAPER_HEADLESS,
    )
    if source_name == "inmuebles24":
        return inmuebles24.scrape(slug=cfg["slug"], **common)
    if source_name == "vivanuncios":
        return vivanuncios.scrape(
            slug=cfg["slug"],
            category=cfg["category"],
            location_id=cfg["location_id"],
            query=cfg.get("query", ""),
            **common,
        )
    raise ValueError(f"Fuente desconocida: {source_name}")


def run_zone_source(storage: Storage, zone: dict, source_name: str, cfg: dict):
    logger.info("Buscando: %s [%s]...", zone["label"], source_name)

    listings, reported_total = _scrape_source(source_name, cfg, zone)
    logger.info("  %d publicaciones activas encontradas.", len(listings))

    if not listings:
        logger.warning(
            "  No se obtuvo ninguna publicación en %s para esta zona. Si esto se repite, "
            "revisa SCRAPER_HEADLESS=false en .env por si el sitio está bloqueando "
            "el navegador headless.",
            source_name,
        )
        return

    new_ids = storage.upsert_listings(listings)
    logger.info("  %d publicaciones nuevas guardadas (el resto ya se conocían).", len(new_ids))

    # Solo damos de baja lo que "desapareció" si la búsqueda de verdad
    # cubrió (más o menos) todo lo que el sitio dice tener para esta
    # zona+fuente. Si por un bloqueo parcial solo alcanzamos a leer una
    # fracción de las páginas, no queremos borrar publicaciones válidas
    # por error (normal y esperado en zonas grandes, que tienen muchas
    # más publicaciones que las que se revisan por corrida).
    current_ids = {l.id for l in listings}
    unique_found = len(current_ids)
    if reported_total and unique_found < reported_total * 0.85:
        logger.info(
            "  Solo se leyeron %d de las %d publicaciones que reporta %s para esta "
            "zona; no se dio de baja nada esta vez.",
            unique_found,
            reported_total,
            source_name,
        )
    else:
        removed = storage.deactivate_missing(current_ids, source=source_name, search_key=zone["key"])
        if removed:
            logger.info("  %d publicaciones ya no están disponibles y se quitaron del panel.", removed)

    if new_ids:
        zone_listings = [l for l in storage.get_active_listings() if l.search_key == zone["key"]]
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
        for zone in ZONES:
            for source_name, cfg in zone["sources"].items():
                run_zone_source(storage, zone, source_name, cfg)
        logger.info("Listo. Abre el panel para ver el detalle: python -m src.dashboard")
    finally:
        storage.close()


if __name__ == "__main__":
    run()
