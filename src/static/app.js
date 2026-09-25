/**
 * Lógica compartida del panel (local y GitHub Pages). Cada página define
 * su propia `fetchData()` (de dónde saca listings/stats) y llama a
 * `initApp(fetchData)` una vez cargado este archivo.
 */

let allListings = [];
let chartInstance = null;
let currentView = "all"; // 'all' | 'favorites'
let searchDebounceTimer = null;

/* ---------------- formato ---------------- */

function money(v) {
  if (v === null || v === undefined) return "—";
  return "$" + Math.round(v).toLocaleString("es-MX");
}

function fmtDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  return d.toLocaleDateString("es-MX", { day: "2-digit", month: "short", year: "numeric" });
}

function daysAgo(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  if (isNaN(d)) return null;
  const diffMs = Date.now() - d.getTime();
  return Math.max(0, Math.floor(diffMs / 86400000));
}

function fmtPublished(iso) {
  const days = daysAgo(iso);
  const dateStr = fmtDate(iso);
  if (days === null) return dateStr;
  const daysLabel = days === 0 ? "hoy" : days === 1 ? "hace 1 día" : `hace ${days} días`;
  return `${dateStr}<br><span style="color:var(--text-muted); font-size:0.72rem;">${daysLabel}</span>`;
}

function fmtAge(years) {
  if (years === null || years === undefined) return "—";
  return years === 0 ? "Nueva" : `${years} años`;
}

const SOURCE_LABELS = { inmuebles24: "Inmuebles24", vivanuncios: "Vivanuncios" };

function fmtAlsoIn(alsoIn) {
  if (!alsoIn || alsoIn.length === 0) return "";
  const names = alsoIn.map((s) => SOURCE_LABELS[s] || s).join(", ");
  return `<span class="also-in">también en ${names}</span>`;
}

function fmtMortgage(m) {
  if (!m || !m.loan_amount) return "—";
  const p20 = m.monthly_payments_net["20"];
  const p25 = m.monthly_payments_net["25"];
  const warn20 = m.exceeds_salary["20"];
  const warn25 = m.exceeds_salary["25"];
  const line = (years, payment, warn) => {
    const style = warn ? ' style="color:var(--bad); font-weight:600;"' : "";
    return `<span${style}>${money(payment)}</span> <span style="color:var(--text-muted); font-size:0.7rem;">(${years}a)</span>`;
  };
  let html = `${line(20, p20, warn20)}<br>${line(25, p25, warn25)}`;
  if (m.exceeds_max_credit) {
    html += `<br><span style="color:var(--bad); font-size:0.66rem;">⚠ supera el crédito máx.</span>`;
  }
  return html;
}

function renderMortgageNote(stats) {
  const el = document.getElementById("mortgage-note");
  const m = stats && stats.mortgage_assumptions;
  if (!el || !m) return;
  const pct = (m.annual_rate * 100).toFixed(2).replace(/\.?0+$/, "");
  const closingPct = (m.closing_costs_pct * 100).toFixed(0);
  const employerPct = (m.employer_contribution_pct * 100).toFixed(0);
  const employerAmount = m.salary * m.employer_contribution_pct;
  el.innerHTML =
    `🏦 <strong>Mensualidad Infonavit (neta)</strong>: enganche ${money(m.down_payment)}, menos ` +
    `~${closingPct}% del precio en gastos de escrituración estimados (ISAI, notario, registro), ` +
    `es lo que de verdad baja el precio de la casa; el resto se financia a tasa fija ${pct}% anual ` +
    `(nivel más alto 2026, salario mayor a 6.6 UMA), a ${m.term_years.join(" y ")} años. ` +
    `A ese pago ya se le resta la aportación patronal obligatoria (${employerPct}% de tu sueldo de ` +
    `${money(m.salary)} = ${money(employerAmount)}/mes), que tu patrón mete directo al crédito una ` +
    `vez que lo tienes activo. Es un cálculo aproximado (no incluye seguros ni la cotización real de ` +
    `un notario); confirma tu tasa y tu descuento de nómina real en Mi Cuenta Infonavit. En rojo: ` +
    `mensualidades que aun así superan ese sueldo.`;
}

function verdictClass(verdict) {
  if (!verdict) return "neutral";
  if (verdict.includes("oportunidad")) return "good";
  if (verdict.includes("arriba")) return "bad";
  return "neutral";
}

function verdictFilterKey(verdict) {
  if (!verdict) return "";
  if (verdict.includes("oportunidad")) return "oportunidad";
  if (verdict.includes("arriba")) return "alto";
  if (verdict.includes("normal")) return "normal";
  return "";
}

/* ---------------- filtros / vista ---------------- */

function populateZoneFilter(searches) {
  const sel = document.getElementById("filter-zone");
  const current = sel.value;
  const options = (searches || []).map(
    (s) => `<option value="${s.key}">${s.label} (${s.count})</option>`
  );
  sel.innerHTML = '<option value="">Todas las zonas</option>' + options.join("");
  sel.value = current || "";
}

function setView(view) {
  currentView = view;
  document.getElementById("tab-all").classList.toggle("active", view === "all");
  document.getElementById("tab-favorites").classList.toggle("active", view === "favorites");
  renderTable();
}

function debouncedRenderTable() {
  clearTimeout(searchDebounceTimer);
  searchDebounceTimer = setTimeout(renderTable, 220);
}

function updateTabCounts() {
  const favCount = allListings.filter((l) => l.favorite).length;
  const allEl = document.getElementById("tab-all-count");
  const favEl = document.getElementById("tab-fav-count");
  if (allEl) allEl.textContent = `(${allListings.length})`;
  if (favEl) favEl.textContent = `(${favCount})`;
}

/* ---------------- favoritos (nube vía favorites.js) ---------------- */

async function toggleFavorite(id, btnEl) {
  const listing = allListings.find((l) => l.id === id);
  if (!listing) return;
  const newValue = !listing.favorite;
  listing.favorite = newValue; // optimista
  renderTable();
  const freshBtn = document.querySelector(`.fav-btn[data-id="${CSS.escape(id)}"]`);
  if (freshBtn) {
    freshBtn.classList.add("pop");
    setTimeout(() => freshBtn.classList.remove("pop"), 320);
  }
  await saveFavorite(id, newValue);
  updateTabCounts();
}

/* ---------------- stats locales (según filtros activos) ---------------- */

function computeLocalStats(rows) {
  const priced = rows.filter((l) => l.price);
  const prices = priced.map((l) => l.price);
  const ppm2 = priced.filter((l) => l.lot_size).map((l) => l.price / l.lot_size);
  const sum = (arr) => arr.reduce((a, b) => a + b, 0);
  const median = (arr) => {
    if (!arr.length) return 0;
    const s = [...arr].sort((a, b) => a - b);
    const mid = Math.floor(s.length / 2);
    return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
  };
  return {
    total_listings: rows.length,
    avg_price: prices.length ? sum(prices) / prices.length : 0,
    median_price: median(prices),
    min_price: prices.length ? Math.min(...prices) : 0,
    max_price: prices.length ? Math.max(...prices) : 0,
    avg_price_per_m2: ppm2.length ? sum(ppm2) / ppm2.length : 0,
  };
}

function renderCards(stats) {
  const cards = [
    { label: "Publicaciones (con este filtro)", value: stats.total_listings ?? 0 },
    { label: "Precio promedio", value: money(stats.avg_price) },
    { label: "Precio mediana", value: money(stats.median_price) },
    { label: "$/m² promedio", value: stats.avg_price_per_m2 ? money(stats.avg_price_per_m2) : "—" },
    { label: "Precio mínimo", value: money(stats.min_price) },
    { label: "Precio máximo", value: money(stats.max_price) },
  ];
  document.getElementById("cards").innerHTML = cards
    .map((c) => `<div class="card"><div class="label">${c.label}</div><div class="value">${c.value}</div></div>`)
    .join("");
}

/* ---------------- tabla ---------------- */

function renderTable() {
  const zoneFilter = document.getElementById("filter-zone").value;
  const search = document.getElementById("search").value.trim().toLowerCase();
  const maxPriceRaw = document.getElementById("filter-max-price").value;
  const maxPrice = maxPriceRaw ? Number(maxPriceRaw) : null;
  const verdictFilter = document.getElementById("filter-verdict").value;
  const sortBy = document.getElementById("sort-by").value;

  let rows = allListings.filter((l) => {
    if (currentView === "favorites" && !l.favorite) return false;
    if (zoneFilter && l.search_key !== zoneFilter) return false;
    if (search) {
      const hay = (l.title || "").toLowerCase() + " " + (l.location || "").toLowerCase();
      if (!hay.includes(search)) return false;
    }
    if (maxPrice !== null && (l.price === null || l.price === undefined || l.price > maxPrice)) return false;
    if (verdictFilter && verdictFilterKey(l.verdict) !== verdictFilter) return false;
    return true;
  });

  renderCards(computeLocalStats(rows));
  renderChart(rows);

  const sorters = {
    first_seen_desc: (a, b) => (b.first_seen || "").localeCompare(a.first_seen || ""),
    first_seen_asc: (a, b) => (a.first_seen || "").localeCompare(b.first_seen || ""),
    price_asc: (a, b) => (a.price ?? Infinity) - (b.price ?? Infinity),
    price_desc: (a, b) => (b.price ?? -Infinity) - (a.price ?? -Infinity),
    ppm2_asc: (a, b) => (a.price_per_m2 ?? Infinity) - (b.price_per_m2 ?? Infinity),
    vs_avg_asc: (a, b) => (a.vs_avg_price_pct ?? Infinity) - (b.vs_avg_price_pct ?? Infinity),
    mortgage20_asc: (a, b) =>
      ((a.mortgage && a.mortgage.monthly_payments_net["20"]) ?? Infinity) -
      ((b.mortgage && b.mortgage.monthly_payments_net["20"]) ?? Infinity),
    age_asc: (a, b) => (a.age_years ?? Infinity) - (b.age_years ?? Infinity),
  };
  rows = rows.sort(sorters[sortBy] || sorters.first_seen_desc);

  document.getElementById("count-note").textContent =
    currentView === "favorites"
      ? `${rows.length} favorita${rows.length === 1 ? "" : "s"}`
      : `${rows.length} de ${allListings.length} publicaciones`;

  const tbody = document.getElementById("table-body");
  const emptyEl = document.getElementById("empty-state");

  if (rows.length === 0) {
    tbody.innerHTML = "";
    if (currentView === "favorites") {
      emptyEl.innerHTML = `<span class="big">🤍</span>Todavía no marcas ninguna favorita.<br>Dale clic al corazón de una publicación para guardarla aquí.`;
    } else if (allListings.length === 0) {
      emptyEl.innerHTML = `<span class="big">🏠</span>No hay publicaciones guardadas todavía.<br>Corre <code>python -m src.main</code> para la primera búsqueda.`;
    } else {
      emptyEl.innerHTML = `<span class="big">🔍</span>Nada coincide con estos filtros.<br>Prueba ajustando la búsqueda o el precio máximo.`;
    }
    emptyEl.style.display = "block";
  } else {
    emptyEl.style.display = "none";
  }

  tbody.innerHTML = rows
    .map((l) => {
      const vClass = verdictClass(l.verdict);
      const vsAvg =
        l.vs_avg_price_pct === null || l.vs_avg_price_pct === undefined
          ? '<span class="badge neutral">sin datos</span>'
          : `<span class="badge ${vClass}">${l.vs_avg_price_pct > 0 ? "+" : ""}${l.vs_avg_price_pct.toFixed(1)}%</span>`;
      const favClass = l.favorite ? "fav-btn is-fav" : "fav-btn";
      const favIcon = l.favorite ? "❤️" : "🤍";
      const idAttr = l.id.replace(/"/g, "&quot;");
      return `
        <tr>
          <td class="fav-cell"><button class="${favClass}" data-id="${idAttr}" onclick="toggleFavorite('${idAttr}')" title="Guardar como favorita">${favIcon}</button></td>
          <td class="title-cell">
            <div class="t" title="${(l.title || "").replace(/"/g, '&quot;')}">${l.title || "(sin título)"}</div>
            <div class="loc">${l.location || ""}</div>
            <span class="zone-tag">${l.search_label || ""}</span>
            ${fmtAlsoIn(l.also_in)}
          </td>
          <td class="num" data-label="Precio">${money(l.price)}</td>
          <td class="num" data-label="m²">${l.lot_size ? Math.round(l.lot_size) : "—"}</td>
          <td class="num" data-label="$/m²">${l.price_per_m2 ? money(l.price_per_m2) : "—"}</td>
          <td class="num" data-label="Rec.">${l.bedrooms ?? "—"}</td>
          <td class="num" data-label="Baños">${l.bathrooms ?? "—"}</td>
          <td class="num" data-label="Antigüedad">${fmtAge(l.age_years)}</td>
          <td data-label="Publicada">${fmtPublished(l.first_seen)}</td>
          <td data-label="vs. promedio">${vsAvg}</td>
          <td class="num" data-label="Mensualidad">${fmtMortgage(l.mortgage)}</td>
          <td class="link-cell"><a class="link-btn" href="${l.url}" target="_blank" rel="noopener">Ver publicación ↗</a></td>
        </tr>`;
    })
    .join("");
}

/* ---------------- gráfica ---------------- */

function renderChart(rows) {
  const priced = rows.filter((l) => l.price);
  if (priced.length === 0) {
    if (chartInstance) {
      chartInstance.destroy();
      chartInstance = null;
    }
    return;
  }

  const prices = priced.map((l) => l.price);
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const bucketCount = 8;
  const bucketSize = Math.max((max - min) / bucketCount, 1);
  const buckets = new Array(bucketCount).fill(0);

  prices.forEach((p) => {
    let idx = Math.floor((p - min) / bucketSize);
    if (idx >= bucketCount) idx = bucketCount - 1;
    if (idx < 0) idx = 0;
    buckets[idx]++;
  });

  const labels = buckets.map((_, i) => {
    const lo = min + i * bucketSize;
    const hi = lo + bucketSize;
    const fmt = (v) => "$" + Math.round(v / 1000) + "k";
    return `${fmt(lo)}–${fmt(hi)}`;
  });

  const styles = getComputedStyle(document.documentElement);
  const accent = styles.getPropertyValue("--accent").trim();
  const text = styles.getPropertyValue("--text-muted").trim();

  if (chartInstance) chartInstance.destroy();
  const ctx = document.getElementById("priceChart").getContext("2d");
  chartInstance = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{ label: "Publicaciones", data: buckets, backgroundColor: accent, borderRadius: 4 }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 260 },
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: text, font: { size: 10 } }, grid: { display: false } },
        y: { ticks: { color: text, precision: 0 }, grid: { color: "rgba(128,128,128,0.15)" } },
      },
    },
  });
}

/* ---------------- estado de sincronización ---------------- */

function renderSyncNote() {
  const el = document.getElementById("sync-note");
  if (!el) return;
  if (isFirebaseConfigured()) {
    el.innerHTML = '<span class="sync-dot"></span> Favoritos sincronizados en la nube';
  } else {
    el.innerHTML =
      '<span class="sync-dot off"></span> Favoritos guardados solo en este dispositivo ' +
      "(configura Firebase para sincronizar entre tu PC y celular — ver README)";
  }
}

/* ---------------- carga inicial ---------------- */

function showSkeleton(show) {
  const skel = document.getElementById("skeleton");
  const content = document.getElementById("content");
  if (skel) skel.style.display = show ? "block" : "none";
  if (content) content.style.display = show ? "none" : "block";
}

async function initApp(fetchData) {
  document.getElementById("filter-zone").addEventListener("change", renderTable);
  document.getElementById("search").addEventListener("input", debouncedRenderTable);
  document.getElementById("filter-max-price").addEventListener("input", debouncedRenderTable);
  document.getElementById("filter-verdict").addEventListener("change", renderTable);
  document.getElementById("sort-by").addEventListener("change", renderTable);
  document.getElementById("tab-all").addEventListener("click", () => setView("all"));
  document.getElementById("tab-favorites").addEventListener("click", () => setView("favorites"));

  const refreshBtn = document.getElementById("refresh-btn");
  if (refreshBtn) refreshBtn.addEventListener("click", () => loadAll(fetchData, true));

  await loadAll(fetchData, false);
}

let _lastKnownUpdate = undefined;

async function loadAll(fetchData, isManualClick) {
  const refreshBtn = document.getElementById("refresh-btn");
  const originalBtnText = refreshBtn ? refreshBtn.textContent : "";
  if (refreshBtn) refreshBtn.disabled = true;
  showSkeleton(true);

  try {
    const [{ listings, stats }, favMap] = await Promise.all([fetchData(), loadFavorites()]);
    allListings = listings;
    allListings.forEach((l) => {
      if (Object.prototype.hasOwnProperty.call(favMap, l.id)) {
        l.favorite = !!favMap[l.id];
      }
    });

    // Confirmación visible de que el botón sí hizo algo, aunque los
    // datos publicados sean los mismos de antes (es normal: esta página
    // solo lee la última "foto" que se publicó desde la PC).
    if (isManualClick && refreshBtn) {
      const changed = _lastKnownUpdate !== undefined && stats.last_update !== _lastKnownUpdate;
      refreshBtn.textContent = changed ? "✓ Hay novedades" : "✓ Ya tenías lo último";
      setTimeout(() => {
        refreshBtn.textContent = originalBtnText;
      }, 2000);
    }
    _lastKnownUpdate = stats.last_update;

    populateZoneFilter(stats.searches);
    renderMortgageNote(stats);
    renderSyncNote();
    updateTabCounts();
    renderTable();

    document.getElementById("last-update").textContent = stats.last_update
      ? "Datos al: " + fmtDate(stats.last_update)
      : "Sin datos aún";
  } finally {
    showSkeleton(false);
    if (refreshBtn) refreshBtn.disabled = false;
  }
}
