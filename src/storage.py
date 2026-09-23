import difflib
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from .scrapers.base import Listing

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "listings.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    title TEXT,
    url TEXT,
    price REAL,
    currency TEXT,
    maintenance REAL,
    lot_size REAL,
    bedrooms INTEGER,
    bathrooms REAL,
    parking INTEGER,
    location TEXT,
    first_seen TEXT,
    last_seen TEXT,
    active INTEGER DEFAULT 1,
    search_key TEXT,
    search_label TEXT,
    age_years INTEGER,
    favorite INTEGER DEFAULT 0,
    also_in TEXT
);
"""
# `favorite` queda en el esquema por compatibilidad con bases de datos
# viejas, pero ya no lo usa el programa: los favoritos ahora se guardan en
# Firebase directo desde el navegador (src/static/favorites.js), para que
# se sincronicen entre dispositivos.

# Si una publicación nueva coincide en zona+precio+m² con una ya activa de
# OTRA fuente, y sus títulos se parecen al menos esto (0-1), se trata como
# la misma propiedad anunciada en dos sitios (muy común) en vez de crear
# una fila duplicada.
_DUP_TITLE_SIMILARITY = 0.55

# Antes de que el programa buscara en varias zonas, todo lo guardado era
# de esta búsqueda. Se usa solo para rellenar registros viejos que no
# tenían search_key/search_label.
_LEGACY_SEARCH_KEY = "casas-san-mateo-atenco"
_LEGACY_SEARCH_LABEL = "Casas en venta — San Mateo Atenco"


@dataclass
class ListingRecord:
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
    first_seen: str
    last_seen: str
    active: int = 1
    search_key: str = _LEGACY_SEARCH_KEY
    search_label: str = _LEGACY_SEARCH_LABEL
    age_years: Optional[int] = None
    favorite: int = 0
    also_in: Optional[str] = None


class Storage:
    def __init__(self, db_path: Path = DB_PATH):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self._ensure_schema()

    def _ensure_schema(self):
        self.conn.execute(SCHEMA)
        cols = {row["name"] for row in self.conn.execute("PRAGMA table_info(listings)")}
        if "active" not in cols:
            self.conn.execute("ALTER TABLE listings ADD COLUMN active INTEGER DEFAULT 1")
        if "search_key" not in cols:
            self.conn.execute("ALTER TABLE listings ADD COLUMN search_key TEXT")
            self.conn.execute("ALTER TABLE listings ADD COLUMN search_label TEXT")
            self.conn.execute(
                "UPDATE listings SET search_key=?, search_label=? WHERE search_key IS NULL",
                (_LEGACY_SEARCH_KEY, _LEGACY_SEARCH_LABEL),
            )
        if "age_years" not in cols:
            self.conn.execute("ALTER TABLE listings ADD COLUMN age_years INTEGER")
        if "favorite" not in cols:
            self.conn.execute("ALTER TABLE listings ADD COLUMN favorite INTEGER DEFAULT 0")
        if "also_in" not in cols:
            self.conn.execute("ALTER TABLE listings ADD COLUMN also_in TEXT")
        self.conn.commit()

    def _find_cross_source_duplicate(self, l: Listing):
        """Busca una publicación ya activa, de OTRA fuente, en la misma
        zona, con el mismo precio y los mismos m² — y título parecido —
        que probablemente sea la misma propiedad anunciada en dos sitios
        (agencias que publican en Inmuebles24 y Vivanuncios a la vez es
        muy común). Devuelve la fila existente o None."""
        if not l.price or not l.lot_size:
            return None
        cur = self.conn.execute(
            """SELECT * FROM listings
               WHERE search_key=? AND price=? AND lot_size=? AND active=1 AND source != ?""",
            (l.search_key, l.price, l.lot_size, l.source),
        )
        for row in cur.fetchall():
            existing_title = (row["title"] or "").strip().lower()[:200]
            new_title = (l.title or "").strip().lower()[:200]
            if not existing_title or not new_title:
                continue
            ratio = difflib.SequenceMatcher(None, existing_title, new_title).ratio()
            if ratio >= _DUP_TITLE_SIMILARITY:
                return row
        return None

    def upsert_listings(self, listings: List[Listing]) -> List[str]:
        """Inserta publicaciones nuevas y actualiza precio/último-visto en las
        existentes (reactivándolas si habían sido dadas de baja). Si una
        publicación nueva parece ser la misma propiedad que ya está guardada
        pero anunciada en otra fuente, no crea una fila aparte — solo anota
        en `also_in` que también aparece ahí y refresca `last_seen`.
        Devuelve la lista de ids que son genuinamente nuevos (no existían
        antes, ni como duplicado). No toca `favorite` de las que ya
        existían — es una marca tuya, no algo que venga del scraper."""
        now = datetime.now(timezone.utc).isoformat()
        new_ids: List[str] = []
        cur = self.conn.cursor()
        for l in listings:
            cur.execute("SELECT id FROM listings WHERE id = ?", (l.id,))
            exists = cur.fetchone()
            if exists:
                cur.execute(
                    """UPDATE listings
                       SET last_seen=?, price=?, title=?, active=1, search_key=?, search_label=?,
                           age_years=?
                       WHERE id=?""",
                    (now, l.price, l.title, l.search_key, l.search_label, l.age_years, l.id),
                )
                continue

            dup = self._find_cross_source_duplicate(l)
            if dup is not None:
                also_in = set(filter(None, (dup["also_in"] or "").split(",")))
                also_in.add(l.source)
                cur.execute(
                    "UPDATE listings SET last_seen=?, active=1, also_in=? WHERE id=?",
                    (now, ",".join(sorted(also_in)), dup["id"]),
                )
                continue

            cur.execute(
                """INSERT INTO listings
                    (id, source, title, url, price, currency, maintenance, lot_size,
                     bedrooms, bathrooms, parking, location, first_seen, last_seen, active,
                     search_key, search_label, age_years, favorite)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?,?,0)""",
                (
                    l.id, l.source, l.title, l.url, l.price, l.currency, l.maintenance,
                    l.lot_size, l.bedrooms, l.bathrooms, l.parking, l.location, now, now,
                    l.search_key, l.search_label, l.age_years,
                ),
            )
            new_ids.append(l.id)
        self.conn.commit()
        return new_ids

    def deactivate_missing(self, current_ids, source: str, search_key: str) -> int:
        """Marca como inactivas (ya no disponibles) las publicaciones de esta
        `source`+`search_key` que estaban activas pero no vinieron en
        `current_ids` (la búsqueda más reciente de esa zona/fuente). No las
        borra, solo deja de mostrarlas."""
        cur = self.conn.execute(
            "SELECT id FROM listings WHERE source=? AND search_key=? AND active=1",
            (source, search_key),
        )
        previously_active = {row["id"] for row in cur.fetchall()}
        to_deactivate = previously_active - set(current_ids)
        if not to_deactivate:
            return 0
        self.conn.executemany(
            "UPDATE listings SET active=0 WHERE id=?", [(i,) for i in to_deactivate]
        )
        self.conn.commit()
        return len(to_deactivate)

    def get_active_listings(self) -> List[ListingRecord]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM listings WHERE active=1")
        return [ListingRecord(**dict(row)) for row in cur.fetchall()]

    def get_by_id(self, listing_id: str) -> Optional[ListingRecord]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM listings WHERE id=?", (listing_id,))
        row = cur.fetchone()
        return ListingRecord(**dict(row)) if row else None

    def close(self):
        self.conn.close()
