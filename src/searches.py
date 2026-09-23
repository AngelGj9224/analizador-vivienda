"""
Zonas/búsquedas que el programa revisa en Inmuebles24. Para agregar una
nueva, primero confirma en el navegador que la URL
`https://www.inmuebles24.com/<slug>.html` de verdad devuelve resultados
(el sitio no siempre usa el patrón que uno esperaría), y luego agrégala
aquí con una `key` única (no la cambies después: es lo que amarra las
publicaciones ya guardadas a su zona) y un `label` para mostrar en el
panel.
"""

SEARCHES = [
    {
        "key": "casas-san-mateo-atenco",
        "label": "Casas en venta — San Mateo Atenco",
        "slug": "casas-en-venta-en-san-mateo-atenco",
    },
    {
        "key": "casas-metepec",
        "label": "Casas en venta — Metepec",
        "slug": "casas-en-venta-en-metepec",
    },
    {
        "key": "deptos-benito-juarez",
        "label": "Departamentos en venta — Benito Juárez, CDMX",
        "slug": "departamentos-en-venta-en-benito-juarez",
    },
]
