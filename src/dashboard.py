"""
Panel local de análisis: lee la base de datos (data/listings.db) que va
llenando src/main.py y la muestra en una página web en tu propia
computadora (http://127.0.0.1:5050). No manda ni recibe nada por internet
más que las librerías de estilo/gráficas (CDN).
"""

import logging
import threading
import webbrowser
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from .export_data import listings_payload, stats_payload
from .storage import Storage

logging.getLogger("werkzeug").setLevel(logging.WARNING)

app = Flask(__name__, template_folder=str(Path(__file__).parent / "templates"))

HOST = "127.0.0.1"
PORT = 5050


@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/api/listings")
def api_listings():
    storage = Storage()
    try:
        return jsonify(listings_payload(storage))
    finally:
        storage.close()


@app.route("/api/stats")
def api_stats():
    storage = Storage()
    try:
        return jsonify(stats_payload(storage))
    finally:
        storage.close()


@app.route("/api/favorite/<listing_id>", methods=["POST"])
def api_favorite(listing_id):
    favorite = bool((request.get_json(silent=True) or {}).get("favorite", True))
    storage = Storage()
    try:
        ok = storage.set_favorite(listing_id, favorite)
        if not ok:
            return jsonify({"error": "no existe esa publicación"}), 404
        return jsonify({"id": listing_id, "favorite": favorite})
    finally:
        storage.close()


def _open_browser():
    webbrowser.open_new_tab(f"http://{HOST}:{PORT}/")


def main():
    threading.Timer(1.0, _open_browser).start()
    app.run(host=HOST, port=PORT, debug=False)


if __name__ == "__main__":
    main()
