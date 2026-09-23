from dataclasses import dataclass
from typing import Optional


@dataclass
class Listing:
    """Una publicación de una casa en venta, ya normalizada."""

    id: str
    source: str
    title: str
    url: str
    price: Optional[float]
    currency: Optional[str]
    maintenance: Optional[float]
    lot_size: Optional[float]
    bedrooms: Optional[int]
    bathrooms: Optional[float]
    parking: Optional[int]
    location: str
    search_key: str
    search_label: str
