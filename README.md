# Analizador de Vivienda — San Mateo Atenco

Busca casas en venta en San Mateo Atenco **cuando tú lo mandas llamar**,
guarda lo que encuentra, y lo muestra en un panel local con el detalle de
cada publicación, comparado contra el resto de la zona (precio, precio por
m², etc.) y con el link directo a cada anuncio.

No corre en segundo plano ni manda notificaciones a ningún lado: es
buscar → guardar → revisar en el panel, cuando tú quieras.

## Qué hace y qué no

- **Fuente de datos:** por ahora solo [Inmuebles24](https://www.inmuebles24.com),
  que es donde probé y confirmé que la búsqueda funciona de forma estable.
  Intenté también con Vivanuncios, Lamudi y Trovit/Mitula, pero sus sistemas
  anti-bot (Cloudflare y similares) bloquearon el acceso automatizado. Si
  más adelante quieres que agregue alguno, dímelo.
- Cada vez que corres la búsqueda, guarda las publicaciones que sean
  nuevas (las que ya tenía las deja igual) en `data/listings.db`.
- También revisa cuáles de las que ya tenías guardadas **ya no aparecen**
  en el sitio (se vendieron, las quitaron, etc.) y las quita del panel —
  no las borra de la base, solo deja de mostrarlas. Por seguridad, esto
  **solo pasa si la búsqueda alcanzó a leer casi todas las páginas** que
  el sitio reporta tener; si un bloqueo del sitio interrumpió la búsqueda
  a la mitad, no se da de baja nada esa vez (para no borrar por error algo
  que sigue en venta).
- El panel muestra, para cada publicación, la fecha en que el programa la
  detectó por primera vez y hace cuántos días fue ("Publicada").
- El panel solo lee esa base de datos — no se conecta a internet más que
  para cargar el estilo/gráfica del panel mismo.

## Instalación

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

(Opcional) copia `.env.example` a `.env` si quieres ajustar cuántas
páginas revisar o forzar el navegador visible:

```bash
cp .env.example .env
```

## Uso

**1. Buscar** (cuando tú quieras, no automático):

```bash
python -m src.main
```

O doble clic en [`buscar_casas.bat`](buscar_casas.bat) desde el
Explorador de Windows (los enlaces dentro del chat solo abren el archivo
como texto, no lo ejecutan — hay que abrirlo desde el Explorador).

Esto imprime en la consola qué encontró y cuántas publicaciones son
nuevas.

**2. Ver el panel de análisis:**

```bash
python -m src.dashboard
```

O doble clic en [`abrir_panel.bat`](abrir_panel.bat). Se abre tu
navegador en `http://127.0.0.1:5050` con:

- Tarjetas resumen (total de publicaciones, precio promedio/mediana,
  $/m² promedio, mínimo y máximo).
- Buscador por colonia/título, filtro por veredicto, y varios órdenes
  (precio, $/m², más baratas vs. el promedio).
- Un botón "Ver publicación" en cada fila que abre el anuncio original.
- Una gráfica de distribución de precios de la zona.

Puedes dejar el panel abierto y solo darle "↻ Actualizar" después de
correr una nueva búsqueda.

## Verla desde tu celular (GitHub Pages)

Puedes publicar una versión de solo lectura en internet, gratis, usando
GitHub Pages. No corre nada en la nube — es una "foto" de tus datos que tú
actualizas cuando quieras desde tu PC.

**Primera vez (configurar):**

1. Crea un repositorio en GitHub (puede ser público; los datos son de
   publicaciones que ya son públicas en Inmuebles24). Si quieres, dime el
   nombre que le quieres poner y te ayudo con los comandos para
   conectarlo.
2. En GitHub: **Settings → Pages → Source**, selecciona la rama `main` y
   la carpeta `/docs`, y guarda. GitHub te da una URL tipo
   `https://tu-usuario.github.io/tu-repo/`.

**Cada vez que quieras actualizar lo que ves en tu celular:**

```bash
python -m src.main        # 1. buscar (opcional si ya buscaste hace poco)
python -m src.publish     # 2. genera docs/index.html, listings.json y stats.json
git add docs/
git commit -m "Actualiza publicaciones"
git push
```

Unos segundos después de hacer `push`, la página en GitHub Pages queda
actualizada y la puedes abrir desde el navegador de tu celular con esa
misma URL.

**Nota de privacidad:** en el plan gratis de GitHub, la página de Pages es
pública — cualquiera con el link la puede ver (aunque no aparece en
buscadores ni es fácil de adivinar). Ya que son datos de casas en venta
públicas, no debería ser un problema, pero tenlo presente.

## Cómo decide si algo es "buena oportunidad"

Cada publicación se compara contra el promedio de todas las casas que ya
están guardadas en `data/listings.db`:

- Si el precio está **15% o más por debajo** del promedio → "posible buena
  oportunidad".
- Si está **20% o más por arriba** → "precio por arriba del promedio".
- Si no, está dentro de un rango normal.

Esos umbrales están en `src/config.py`
(`UMBRAL_BUENA_OPORTUNIDAD_PCT`, `UMBRAL_PRECIO_ALTO_PCT`) si los quieres
ajustar. Entre más publicaciones acumule la base de datos, más
representativa será la comparación.

## Estructura del proyecto

```
src/
  main.py               busca y guarda (una sola corrida, manual)
  dashboard.py           panel local de análisis (Flask, http://127.0.0.1:5050)
  publish.py              genera la versión estática para GitHub Pages (docs/)
  export_data.py          lógica compartida de datos (usada por dashboard y publish)
  templates/
    dashboard.html         interfaz del panel local
    dashboard_static.html   interfaz de la versión publicada en GitHub Pages
  config.py              configuración (lee .env)
  storage.py              base de datos SQLite (data/listings.db)
  analysis.py             cálculo de estadísticas y comparación
  scrapers/
    inmuebles24.py         scraper de Inmuebles24
docs/                     versión estática generada (esto es lo que ve GitHub Pages)
buscar_casas.bat         doble clic para buscar (desde el Explorador)
abrir_panel.bat          doble clic para abrir el panel (desde el Explorador)
```

## Notas y limitaciones

- Estos sitios cambian su HTML de vez en cuando; si el programa deja de
  encontrar resultados, probablemente hay que actualizar los selectores en
  `src/scrapers/inmuebles24.py`.
- Si `SCRAPER_HEADLESS=true` empieza a devolver 0 resultados de forma
  consistente, prueba poniéndolo en `false` en `.env` para ver qué está
  pasando (se abrirá una ventana de Chromium visible).
