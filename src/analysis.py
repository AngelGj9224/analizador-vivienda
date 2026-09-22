import statistics
from dataclasses import dataclass
from typing import List, Optional

from . import config
from .storage import ListingRecord


@dataclass
class MarketStats:
    count: int
    avg_price: float
    median_price: float
    min_price: float
    max_price: float
    avg_price_per_m2: float


def compute_market_stats(listings: List[ListingRecord]) -> MarketStats:
    priced = [l for l in listings if l.price]
    prices = [l.price for l in priced]
    ppm2 = [l.price / l.lot_size for l in priced if l.lot_size and l.lot_size > 0]

    return MarketStats(
        count=len(priced),
        avg_price=statistics.mean(prices) if prices else 0.0,
        median_price=statistics.median(prices) if prices else 0.0,
        min_price=min(prices) if prices else 0.0,
        max_price=max(prices) if prices else 0.0,
        avg_price_per_m2=statistics.mean(ppm2) if ppm2 else 0.0,
    )


def compare_listing(listing: ListingRecord, stats: MarketStats) -> dict:
    """Compara una publicación contra el resto del mercado ya guardado."""
    result = {
        "vs_avg_price_pct": None,
        "vs_avg_ppm2_pct": None,
        "verdict": "Sin suficientes datos todavía para comparar (sigue guardando publicaciones).",
    }

    if not stats.avg_price or not listing.price:
        return result

    vs_price = (listing.price - stats.avg_price) / stats.avg_price * 100
    result["vs_avg_price_pct"] = vs_price

    if stats.avg_price_per_m2 and listing.lot_size:
        ppm2 = listing.price / listing.lot_size
        result["vs_avg_ppm2_pct"] = (ppm2 - stats.avg_price_per_m2) / stats.avg_price_per_m2 * 100

    if vs_price <= config.UMBRAL_BUENA_OPORTUNIDAD_PCT:
        result["verdict"] = "Posible buena oportunidad: precio bajo comparado con el resto de la zona."
    elif vs_price >= config.UMBRAL_PRECIO_ALTO_PCT:
        result["verdict"] = "Precio por arriba del promedio de la zona."
    else:
        result["verdict"] = "Precio dentro del rango normal de la zona."

    return result
