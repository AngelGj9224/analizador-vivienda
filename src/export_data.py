"""
Arma la información de publicaciones/estadísticas en el mismo formato que
usan tanto el panel local (Flask, src/dashboard.py) como la publicación
estática para GitHub Pages (src/publish.py), para no duplicar la lógica.

Las estadísticas de mercado (promedio, mediana, etc.) y la comparación de
cada publicación ("vs. promedio") se calculan POR ZONA/BÚSQUEDA
(search_key) — comparar el precio de un departamento en Benito Juárez
contra el de una casa en Metepec no tendría sentido.
"""

from collections import defaultdict

from . import mortgage
from .analysis import compare_listing, compute_market_stats
from .searches import SEARCHES
from .storage import Storage


def listings_payload(storage: Storage) -> list:
    listings = storage.get_active_listings()

    by_search = defaultdict(list)
    for l in listings:
        by_search[l.search_key].append(l)
    stats_by_search = {key: compute_market_stats(group) for key, group in by_search.items()}

    data = []
    for l in listings:
        stats = stats_by_search[l.search_key]
        comparison = compare_listing(l, stats)
        price_per_m2 = (l.price / l.lot_size) if (l.price and l.lot_size) else None
        data.append(
            {
                "id": l.id,
                "source": l.source,
                "title": l.title,
                "url": l.url,
                "price": l.price,
                "currency": l.currency,
                "maintenance": l.maintenance,
                "lot_size": l.lot_size,
                "bedrooms": l.bedrooms,
                "bathrooms": l.bathrooms,
                "parking": l.parking,
                "location": l.location,
                "first_seen": l.first_seen,
                "last_seen": l.last_seen,
                "price_per_m2": price_per_m2,
                "search_key": l.search_key,
                "search_label": l.search_label,
                "vs_avg_price_pct": comparison["vs_avg_price_pct"],
                "vs_avg_ppm2_pct": comparison["vs_avg_ppm2_pct"],
                "verdict": comparison["verdict"],
                "mortgage": mortgage.estimate(l.price),
            }
        )
    return data


def stats_payload(storage: Storage) -> dict:
    listings = storage.get_active_listings()
    stats = compute_market_stats(listings)
    last_seen_values = [l.last_seen for l in listings if l.last_seen]

    counts_by_key = defaultdict(int)
    for l in listings:
        counts_by_key[l.search_key] += 1
    searches = [
        {"key": s["key"], "label": s["label"], "count": counts_by_key.get(s["key"], 0)}
        for s in SEARCHES
    ]

    return {
        "total_listings": len(listings),
        "count_with_price": stats.count,
        "avg_price": stats.avg_price,
        "median_price": stats.median_price,
        "min_price": stats.min_price,
        "max_price": stats.max_price,
        "avg_price_per_m2": stats.avg_price_per_m2,
        "last_update": max(last_seen_values) if last_seen_values else None,
        "searches": searches,
        "mortgage_assumptions": {
            "down_payment": mortgage.DOWN_PAYMENT,
            "annual_rate": mortgage.ANNUAL_RATE,
            "salary": mortgage.SALARY,
            "term_years": list(mortgage.TERM_YEARS),
            "max_credit_tradicional": mortgage.MAX_CREDIT_TRADICIONAL,
            "closing_costs_pct": mortgage.CLOSING_COSTS_PCT,
            "employer_contribution_pct": mortgage.EMPLOYER_CONTRIBUTION_PCT,
        },
    }
