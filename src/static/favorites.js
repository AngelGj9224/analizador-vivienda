/**
 * Favoritos sincronizados en la nube (Firebase Firestore), compartidos
 * entre el panel local y la versión publicada en GitHub Pages. Si
 * firebase_config.js todavía tiene los valores de ejemplo (proyecto no
 * configurado), cae de vuelta a localStorage (favoritos solo en este
 * navegador) para que la función no se rompa mientras configuras Firebase.
 *
 * Requiere que, ANTES de este script, se hayan cargado:
 *   - firebase_config.js (define window.FIREBASE_CONFIG)
 *   - los SDK de Firebase (app + firestore, compat)
 */

let _favDb = null;
let _favDbTried = false;

function isFirebaseConfigured() {
  const c = window.FIREBASE_CONFIG;
  return !!(c && c.apiKey && !String(c.apiKey).startsWith("TU_"));
}

function _initFavoritesDb() {
  if (_favDbTried) return _favDb;
  _favDbTried = true;
  if (!isFirebaseConfigured() || typeof firebase === "undefined") return null;
  try {
    firebase.initializeApp(window.FIREBASE_CONFIG);
    _favDb = firebase.firestore();
  } catch (e) {
    console.error("No se pudo iniciar Firebase, uso localStorage:", e);
    _favDb = null;
  }
  return _favDb;
}

function _getLocalFavorites() {
  try {
    return JSON.parse(localStorage.getItem("favorites") || "{}");
  } catch (e) {
    return {};
  }
}

function _setLocalFavorite(id, value) {
  try {
    const favs = _getLocalFavorites();
    if (value) favs[id] = true;
    else delete favs[id];
    localStorage.setItem("favorites", JSON.stringify(favs));
  } catch (e) {
    // localStorage no disponible (modo privado, etc.)
  }
}

/** Devuelve un mapa {id: true} con los favoritos guardados. */
async function loadFavorites() {
  const db = _initFavoritesDb();
  if (!db) return _getLocalFavorites();
  try {
    const snap = await db.collection("favorites").get();
    const map = {};
    snap.forEach((doc) => {
      map[doc.id] = true;
    });
    return map;
  } catch (e) {
    console.error("No se pudieron leer los favoritos de la nube, uso localStorage:", e);
    return _getLocalFavorites();
  }
}

/** Marca/desmarca un favorito. Devuelve true si quedó sincronizado en la nube. */
async function saveFavorite(id, value) {
  const db = _initFavoritesDb();
  if (!db) {
    _setLocalFavorite(id, value);
    return false;
  }
  try {
    if (value) {
      await db.collection("favorites").doc(id).set({ ts: Date.now() });
    } else {
      await db.collection("favorites").doc(id).delete();
    }
    return true;
  } catch (e) {
    console.error("No se pudo guardar en la nube, lo guardo local:", e);
    _setLocalFavorite(id, value);
    return false;
  }
}
