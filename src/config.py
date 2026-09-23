import os

from dotenv import load_dotenv

load_dotenv()

SCRAPER_HEADLESS = os.getenv("SCRAPER_HEADLESS", "true").lower() == "true"
MAX_PAGES = int(os.getenv("MAX_PAGES", "3"))

# Un listado se considera "buena oportunidad" si su precio está al menos este
# porcentaje por debajo del promedio de la zona (comparando contra las demás
# publicaciones activas guardadas en la base de datos).
UMBRAL_BUENA_OPORTUNIDAD_PCT = -15
UMBRAL_PRECIO_ALTO_PCT = 20
