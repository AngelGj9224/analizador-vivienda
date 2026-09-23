"""
Zonas que el programa revisa, y en qué sitios (fuentes) busca cada una.

Cada zona tiene una `key` única (no la cambies después: amarra las
publicaciones ya guardadas a su zona) y un `label` para mostrar en el
panel. Dentro, `sources` trae la configuración específica de cada sitio
para esa misma zona — así una casa en San Mateo Atenco encontrada en
Inmuebles24 y otra encontrada en Vivanuncios se comparan entre sí como
parte del mismo mercado, aunque vengan de sitios distintos.

Para agregar una zona/fuente nueva: usa el buscador del sitio (escribe la
ubicación, elige el tipo de inmueble, dale Comprar/Buscar) y copia los
datos de la URL resultante — no los adivines, algunos sitios usan ids
numéricos de ubicación que no se pueden deducir.
"""

ZONES = [
    {
        "key": "casas-san-mateo-atenco",
        "label": "Casas en venta — San Mateo Atenco",
        "sources": {
            "inmuebles24": {
                "slug": "casas-en-venta-en-san-mateo-atenco",
            },
            "vivanuncios": {
                "slug": "san-mateo-atenco",
                "category": 1097,
                "location_id": 10728,
                "query": "pt=1,101,12",
            },
        },
    },
    {
        "key": "casas-metepec",
        "label": "Casas en venta — Metepec",
        "sources": {
            "inmuebles24": {
                "slug": "casas-en-venta-en-metepec",
            },
            "vivanuncios": {
                "slug": "metepec-edomex",
                "category": 1097,
                "location_id": 10707,
                "query": "pt=1,101,12",
            },
        },
    },
    {
        "key": "deptos-benito-juarez",
        "label": "Departamentos en venta — Benito Juárez, CDMX",
        "sources": {
            "inmuebles24": {
                "slug": "departamentos-en-venta-en-benito-juarez",
            },
            "vivanuncios": {
                "slug": "benito-juarez",
                "category": 1294,
                "location_id": 10267,
                "query": "",
            },
        },
    },
]
