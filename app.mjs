import { esHoja, recogerHojas, escHtml, highlight, renderStars, pathStr } from './utils.mjs';
import { renderArbolDebug, actualizarEstrellaDebugLibro, actualizarEstrellaDebugGenero } from './debug.mjs';

// ══════════════════════════════════════════════════════════
// ESTADO GLOBAL
// ══════════════════════════════════════════════════════════
let datosGlobales   = null;
let todasHojasFlat  = [];
let similarMap      = {};
let misRatings      = {};  // { book_id: 1-5 }
let misGenreRatings = {};  // { nodeId: 1-5 }
let modoDebug       = false;
let mostrarPR       = false;
let sinPrior        = false;  // true = desactivar corrección bayesiana
let parentMap       = {};  // { childId: parentId } construido tras cada calcular()

try { misRatings = JSON.parse(localStorage.getItem('bookrank_ratings') || '{}'); } catch (e) {}
try { misGenreRatings = JSON.parse(localStorage.getItem('bookrank_genre_ratings') || '{}'); } catch (e) {}

const PAGE_SIZE    = 10;
const SEARCH_LIMIT = 50;

// ══════════════════════════════════════════════════════════
// INIT
// ══════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('btn-calc').addEventListener('click', () => calcular(false));
    document.getElementById('btn-baseline').addEventListener('click', () => calcular(true));

    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab, btn));
    });

    document.getElementById('search-input').addEventListener('input', e => {
        debouncedSearch(e.target.value);
    });
    document.getElementById('search-clear').addEventListener('click', limpiarBusqueda);
    document.getElementById('btn-debug').addEventListener('click', toggleDebug);
    document.getElementById('btn-ver-pr').addEventListener('click', toggleVerPR);
    document.getElementById('btn-sin-prior').addEventListener('click', toggleSinPrior);
});

function toggleVerPR() {
    mostrarPR = !mostrarPR;
    const btn = document.getElementById('btn-ver-pr');
    btn.classList.toggle('active', mostrarPR);
    btn.textContent = mostrarPR ? '🧮 PageRank ON' : '🧮 Ver PageRank';
    if (datosGlobales?.arbol) renderArbol(datosGlobales.arbol);
}

function toggleSinPrior() {
    sinPrior = !sinPrior;
    const btn = document.getElementById('btn-sin-prior');
    btn.classList.toggle('active', sinPrior);
    btn.textContent = sinPrior ? '📉 Sin prior ON' : '📉 Sin prior';
}

// ══════════════════════════════════════════════════════════
// MODO DEBUG
// ══════════════════════════════════════════════════════════

// Empaqueta las funciones de estado que debug.mjs necesita para ser interactivo
function mkDebugCallbacks() {
    return {
        misRatings,
        misGenreRatings,
        pesoEfectivo,
        tieneValoracionPropia,
        rateBook,
        rateGenre,
        abrirPanelLibro,
    };
}

function toggleDebug() {
    modoDebug = !modoDebug;
    const btn = document.getElementById('btn-debug');
    btn.classList.toggle('active', modoDebug);
    btn.textContent = modoDebug ? '🐛 Debug ON' : '🐛 Debug';
    document.getElementById('debug-panel').style.display   = modoDebug ? 'flex' : 'none';
    document.getElementById('main-panels').style.display   = modoDebug ? 'none' : 'grid';
    if (modoDebug && datosGlobales) renderArbolDebug(datosGlobales.arbol, mkDebugCallbacks());
}

// ══════════════════════════════════════════════════════════
// TABS
// ══════════════════════════════════════════════════════════
function switchTab(id, btn) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab-' + id).classList.add('active');
}

// ══════════════════════════════════════════════════════════
// CALCULAR — envía también las valoraciones del usuario
// ══════════════════════════════════════════════════════════
async function calcular(baseline = false) {
    const btn     = document.getElementById('btn-calc');
    const overlay = document.getElementById('overlay');

    btn.disabled    = true;
    btn.textContent = baseline ? 'Cargando baseline…' : 'Calculando…';
    overlay.classList.add('show');

    try {
        // Solo enviamos ratings con valor > 0
        const ratingsParaEnviar = Object.fromEntries(
            Object.entries(misRatings).filter(([, v]) => v > 0)
        );

        const res = await fetch('http://localhost:8080', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                peso_libro:          3,
                peso_referencia:     3,
                user_ratings:        ratingsParaEnviar,
                user_genre_ratings:  misGenreRatings,
                debug_mode:          modoDebug,
                baseline:            baseline,
                aplicar_prior:       !sinPrior
            })
        });

        datosGlobales = await res.json();
        if (datosGlobales.similar_map) similarMap = datosGlobales.similar_map;

        parentMap = {};
        buildParentMap(datosGlobales.arbol);

        todasHojasFlat = [];
        recogerHojas(datosGlobales.arbol, todasHojasFlat, []);
        todasHojasFlat.sort((a, b) => b.valor - a.valor);

        renderPopular();
        renderPersonal();
        renderMisGeneros();
        renderRecomendaciones();
        renderArbol(datosGlobales.arbol);
        if (modoDebug) renderArbolDebug(datosGlobales.arbol, mkDebugCallbacks());
        btn.textContent = 'Actualizar';

    } catch (err) {
        console.error(err);
        alert('Error de conexión. ¿Está server.py encendido?');
        btn.textContent = 'Reintentar';
    } finally {
        btn.disabled = false;
        overlay.classList.remove('show');
    }
}

// ══════════════════════════════════════════════════════════
// HELPERS
// ══════════════════════════════════════════════════════════

function buildNombreMap(nodo, acc = {}) {
    if (nodo.id) acc[nodo.id] = nodo.nombre;
    (nodo.hijos || []).forEach(h => buildNombreMap(h, acc));
    return acc;
}

function buildParentMap(nodo, parent = null) {
    if (parent && nodo.id) parentMap[nodo.id] = parent.id;
    (nodo.hijos || []).forEach(h => buildParentMap(h, nodo));
}

// Rating efectivo de un libro:
//   1) valoración propia del usuario (misRatings)
//   2) score efectivo del servidor (bayesiano con prior, raw sin prior)
//   3) average_rating del dataset como fallback
function ratingEfectivoLibro(hoja) {
    const myR = misRatings[hoja.id];
    if (myR > 0) return myR;
    if (typeof hoja.score_efectivo === 'number') return hoja.score_efectivo;
    return hoja.average_rating || 0;
}

// ── Peso efectivo de un nodo ──────────────────────────────
// Cada nodo es independiente:
//   - Hoja (libro): mi valoración si existe, si no average_rating.
//   - Intermedio: mi valoración de categoría si existe, si no la
//     media de average_rating de sus libros descendientes.
function pesoEfectivo(nodo) {
    if (esHoja(nodo)) return ratingEfectivoLibro(nodo);

    const myG = misGenreRatings[nodo.id];
    if (myG > 0) return myG;

    const hojas = [];
    recogerHojas(nodo, hojas, []);
    if (!hojas.length) return 0;
    const suma = hojas.reduce((acc, h) => acc + ratingEfectivoLibro(h), 0);
    return suma / hojas.length;
}

// True si el peso mostrado proviene de una valoración propia del usuario
// sobre este nodo (no cascadea).
function tieneValoracionPropia(nodo) {
    if (esHoja(nodo)) return (misRatings[nodo.id] || 0) > 0;
    return (misGenreRatings[nodo.id] || 0) > 0;
}

function fmtPeso(val, esPropio) {
    if (!val || val === 0) return '';
    const estrella = esPropio ? '★' : '★';
    return `<span class="peso-medio${esPropio ? ' peso-propio' : ''}">${estrella} (${val.toFixed(2)})</span>`;
}

// ══════════════════════════════════════════════════════════
// RENDER — POPULAR
// ══════════════════════════════════════════════════════════
function renderPopular() {
    if (!datosGlobales) return;
    const top = [...todasHojasFlat].sort((a, b) => b.valor - a.valor).slice(0, 10);
    const container = document.getElementById('list-popular');
    container.innerHTML = '';
    top.forEach((libro, i) => container.appendChild(mkCard(libro, i + 1, true, false)));
}

// ══════════════════════════════════════════════════════════
// RENDER — PERSONAL (libros)
// ══════════════════════════════════════════════════════════
function renderPersonal() {
    if (!datosGlobales) return;
    const container = document.getElementById('list-personal');
    const ratedIds  = Object.keys(misRatings).filter(id => misRatings[id] > 0);

    if (!ratedIds.length) {
        container.innerHTML = `<div class="empty-state"><div class="icon">⭐</div><p>Valora libros en el explorador<br>y aparecerán aquí.</p></div>`;
        return;
    }

    const hojaMap = Object.fromEntries(todasHojasFlat.map(h => [h.id, h]));
    const scored  = ratedIds
        .filter(id => hojaMap[id])
        .map(id => ({ ...hojaMap[id], _s: misRatings[id] * hojaMap[id].valor }))
        .sort((a, b) => b._s - a._s);

    container.innerHTML = '';
    if (!scored.length) {
        container.innerHTML = `<div class="empty-state"><div class="icon">🔍</div><p>No encontrados en el dataset.</p></div>`;
        return;
    }
    scored.forEach((libro, i) => container.appendChild(mkCard(libro, i + 1, true, true)));
}

// ══════════════════════════════════════════════════════════
// RENDER — MIS GÉNEROS VALORADOS
// ══════════════════════════════════════════════════════════
function renderMisGeneros() {
    const container = document.getElementById('list-mis-generos');
    if (!container) return;

    const ratedIds = Object.keys(misGenreRatings).filter(id => misGenreRatings[id] > 0);

    if (!ratedIds.length) {
        container.innerHTML = `<div class="empty-state"><div class="icon">📂</div><p>Valora géneros en el explorador<br>y aparecerán aquí.</p></div>`;
        return;
    }

    const nodoMap = {};
    function indexarNodos(nodo) {
        if (nodo.id) nodoMap[nodo.id] = nodo;
        (nodo.hijos || []).forEach(indexarNodos);
    }
    if (datosGlobales?.arbol) indexarNodos(datosGlobales.arbol);

    container.innerHTML = '';
    ratedIds
        .sort((a, b) => (misGenreRatings[b] || 0) - (misGenreRatings[a] || 0))
        .forEach(id => {
            const nodo   = nodoMap[id];
            const nombre = nodo?.nombre || id;
            const rating = misGenreRatings[id] || 0;
            const pm     = nodo ? pesoEfectivo(nodo) : 0;
            const esPropio = nodo ? tieneValoracionPropia(nodo) : false;

            const card = document.createElement('div');
            card.className = 'book-card';
            card.innerHTML = `
                <div class="book-rank" style="font-size:1rem">📂</div>
                <div class="book-info" style="flex:1">
                    <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
                        <div class="book-title">${escHtml(nombre)}</div>
                        ${pm ? fmtPeso(pm, esPropio) : ''}
                    </div>
                    <div class="genre-stars-row" data-genre-id="${id}">
                        ${[1,2,3,4,5].map(s =>
                            `<span class="genre-star${s <= rating ? ' lit' : ''}" data-star="${s}" data-genre-id="${id}">★</span>`
                        ).join('')}
                    </div>
                </div>
                <button class="btn-quitar" data-clear-genre="${id}" title="Quitar valoración">Quitar opinión</button>`;
            container.appendChild(card);
        });
}

// ══════════════════════════════════════════════════════════
// RENDER — RECOMENDACIONES
// ══════════════════════════════════════════════════════════
function renderRecomendaciones() {
    if (!datosGlobales) return;
    const container = document.getElementById('list-recomendaciones');
    const ratedIds  = Object.keys(misRatings).filter(id => misRatings[id] > 0);

    if (!ratedIds.length) {
        container.innerHTML = `<div class="empty-state"><div class="icon">🔮</div><p>Basadas en libros similares<br>a los que más te han gustado.</p></div>`;
        return;
    }

    const hojaMap    = Object.fromEntries(todasHojasFlat.map(h => [h.id, h]));
    const ratedSet   = new Set(ratedIds);
    const candidatos = {};

    if (Object.keys(similarMap).length) {
        ratedIds.forEach(id => {
            const myR = misRatings[id] || 0;
            (similarMap[id] || []).forEach(sid => {
                if (!ratedSet.has(sid) && hojaMap[sid])
                    candidatos[sid] = (candidatos[sid] || 0) + myR * hojaMap[sid].valor;
            });
        });
    }

    if (!Object.keys(candidatos).length) {
        const generoScore = {};
        ratedIds.forEach(id => {
            const h = hojaMap[id];
            if (h?.path) {
                const g = h.path[h.path.length - 1];
                generoScore[g] = (generoScore[g] || 0) + (misRatings[id] || 0);
            }
        });
        todasHojasFlat.forEach(h => {
            if (ratedSet.has(h.id) || !h.path) return;
            const g = h.path[h.path.length - 1];
            if (generoScore[g]) candidatos[h.id] = h.valor * generoScore[g];
        });
    }

    const recs = Object.entries(candidatos)
        .filter(([id]) => hojaMap[id])
        .sort(([, a], [, b]) => b - a)
        .slice(0, 10)
        .map(([id]) => hojaMap[id]);

    container.innerHTML = '';
    if (!recs.length) {
        container.innerHTML = `<div class="empty-state"><div class="icon">🔮</div><p>Valora más libros para<br>obtener recomendaciones.</p></div>`;
        return;
    }
    recs.forEach((libro, i) => container.appendChild(mkCardRec(libro, i + 1)));
}

// ══════════════════════════════════════════════════════════
// TARJETAS
// ══════════════════════════════════════════════════════════
function mkCard(libro, rank, showGenre, showMyRating) {
    const card  = document.createElement('div');
    card.className  = 'book-card';
    card.dataset.id = libro.id;

    const myR     = misRatings[libro.id] || 0;
    const pm      = ratingEfectivoLibro(libro);
    const esPropio = myR > 0;
    const genHtml = showGenre ? `<span class="book-genre">${escHtml(pathStr(libro))}</span>` : '';
    const myRatingHtml = (showMyRating && myR > 0)
        ? `<div class="my-rating-label">Tu valoración: ${myR}/5</div>` : '';
    const quitarBtn = showMyRating && myR > 0
        ? `<button class="btn-quitar" data-clear-book="${libro.id}" title="Quitar valoración">Quitar opinión</button>` : '';

    card.innerHTML = `
        <div class="book-rank">${rank}</div>
        <div class="book-info" style="flex:1">
            <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
                <div class="book-title">${escHtml(libro.nombre)}</div>
                ${pm ? fmtPeso(pm, esPropio) : ''}
            </div>
            ${genHtml}
            <div class="stars-wrap" data-id="${libro.id}">
                ${renderStars(libro.id, myR, 'star')}
            </div>
            ${myRatingHtml}
        </div>
        ${quitarBtn}`;

    card.style.cursor = 'pointer';
    card.addEventListener('click', e => {
        if (!e.target.closest('[data-star]') && !e.target.closest('.btn-quitar'))
            abrirPanelLibro(libro);
    });
    return card;
}

function mkCardRec(libro, rank) {
    const card  = document.createElement('div');
    card.className  = 'book-card rec';
    card.dataset.id = libro.id;

    const myR    = misRatings[libro.id] || 0;
    const pm     = ratingEfectivoLibro(libro);
    const esPropio = myR > 0;

    card.innerHTML = `
        <div class="book-rank rec-icon">✦</div>
        <div class="book-info">
            <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
                <div class="book-title">${escHtml(libro.nombre)}</div>
                ${pm ? fmtPeso(pm, esPropio) : ''}
            </div>
            <span class="book-genre">${escHtml(pathStr(libro))}</span>
            <div class="stars-wrap" data-id="${libro.id}">
                ${renderStars(libro.id, myR, 'star')}
            </div>
        </div>`;
    card.style.cursor = 'pointer';
    card.addEventListener('click', e => {
        if (!e.target.closest('[data-star]')) abrirPanelLibro(libro);
    });
    return card;
}

// ══════════════════════════════════════════════════════════
// RATING — LIBROS
// ══════════════════════════════════════════════════════════
function rateBook(id, stars) {
    misRatings[id] = (misRatings[id] === stars) ? 0 : stars;
    try { localStorage.setItem('bookrank_ratings', JSON.stringify(misRatings)); } catch (e) {}

    const v = misRatings[id];

    // Actualizar estrellas en el DOM
    document.querySelectorAll(`.stars-wrap[data-id="${id}"] .star`).forEach(s =>
        s.classList.toggle('lit', parseInt(s.dataset.star) <= v));
    document.querySelectorAll(`.leaf-stars-row[data-id="${id}"] .leaf-star`).forEach(s =>
        s.classList.toggle('lit', parseInt(s.dataset.star) <= v));
    document.querySelectorAll(`.sri-stars[data-id="${id}"] .sri-star`).forEach(s =>
        s.classList.toggle('lit', parseInt(s.dataset.star) <= v));

    // Actualizar el peso mostrado en el nodo hoja del árbol
    actualizarPesoNodoArbol(id);
    // Refrescar la media de los nodos intermedios que contienen este libro
    actualizarPesosAncestros(id);

    // Mostrar/ocultar botón ✕ en el árbol
    actualizarBtnQuitarArbol(id, v);

    // Sincronizar árbol debug si está activo
    if (modoDebug) actualizarEstrellaDebugLibro(id, v);

    renderPersonal();
    renderRecomendaciones();
}

// ══════════════════════════════════════════════════════════
// RATING — GÉNEROS Y SUBGÉNEROS
// ══════════════════════════════════════════════════════════
function rateGenre(id, stars) {
    misGenreRatings[id] = (misGenreRatings[id] === stars) ? 0 : stars;
    try { localStorage.setItem('bookrank_genre_ratings', JSON.stringify(misGenreRatings)); } catch (e) {}

    const v = misGenreRatings[id];
    document.querySelectorAll(`.genre-stars-row[data-genre-id="${id}"] .genre-star`).forEach(s =>
        s.classList.toggle('lit', parseInt(s.dataset.star) <= v));

    // Sincronizar árbol debug si está activo
    if (modoDebug) actualizarEstrellaDebugGenero(id, v);

    renderMisGeneros();

    // Actualizar quirúrgicamente solo este nodo y sus ancestros — sin re-renderizar
    // el árbol completo, así se preserva el estado expandido/colapsado.
    actualizarPesoCategoria(id);
    actualizarPesosAncestros(id);
}

// Actualiza el texto de peso del nodo hoja en el árbol cuando se valora un libro
function actualizarPesoNodoArbol(bookId) {
    const wrapper = document.querySelector(`#tree-container [data-id="${bookId}"]`);
    if (!wrapper) return;
    const hoja = todasHojasFlat.find(h => h.id === bookId);
    if (!hoja) return;
    const pm  = ratingEfectivoLibro(hoja);
    const esPropio = (misRatings[bookId] || 0) > 0;
    const row = wrapper.querySelector('.node-row');
    if (!row) return;
    let pesoEl = row.querySelector('.node-peso');
    if (!pesoEl) {
        pesoEl = document.createElement('span');
        row.appendChild(pesoEl);
    }
    pesoEl.className = `node-peso${esPropio ? ' peso-propio' : ''}`;
    pesoEl.textContent = pm ? `★ (${pm.toFixed(2)})` : '';
}

// Busca un nodo por id dentro del árbol JSON cargado
function findNodeInTree(nodo, targetId) {
    if (!nodo) return null;
    if (nodo.id === targetId) return nodo;
    for (const child of (nodo.hijos || [])) {
        const found = findNodeInTree(child, targetId);
        if (found) return found;
    }
    return null;
}

// Actualiza in-place el peso mostrado para un nodo de categoría (intermedio)
// sin re-renderizar el árbol — preserva el estado expandido/colapsado.
function actualizarPesoCategoria(categoryId) {
    const wrapper = document.querySelector(`#tree-container [data-id="${categoryId}"]`);
    if (!wrapper) return;
    const row = wrapper.querySelector('.node-row');
    if (!row) return;
    const nodo = findNodeInTree(datosGlobales?.arbol, categoryId);
    if (!nodo) return;

    const pm = pesoEfectivo(nodo);
    const esPropio = tieneValoracionPropia(nodo);

    let pesoEl = row.querySelector('.node-peso');
    if (pm) {
        if (!pesoEl) {
            pesoEl = document.createElement('span');
            const label = row.querySelector('.node-label');
            if (label && label.nextSibling) row.insertBefore(pesoEl, label.nextSibling);
            else row.appendChild(pesoEl);
        }
        pesoEl.className = `node-peso${esPropio ? ' peso-propio' : ''}`;
        pesoEl.textContent = `★ (${pm.toFixed(2)})`;
    } else if (pesoEl) {
        pesoEl.remove();
    }
}

// Recorre el árbol hacia arriba y actualiza los pesos de todos los ancestros.
// Necesario cuando cambia una hoja o categoría: la media de los intermedios
// que dependen de hojas también puede haber cambiado.
function actualizarPesosAncestros(nodeId) {
    let current = parentMap[nodeId];
    while (current) {
        actualizarPesoCategoria(current);
        current = parentMap[current];
    }
}

// Muestra u oculta el botón ✕ junto al libro en el árbol
function actualizarBtnQuitarArbol(bookId, rating) {
    const wrapper = document.querySelector(`#tree-container [data-id="${bookId}"]`);
    if (!wrapper) return;
    const starsRow = wrapper.querySelector('.leaf-stars-row');
    if (!starsRow) return;

    let btnExistente = wrapper.querySelector('.btn-quitar-arbol');
    if (rating > 0) {
        if (!btnExistente) {
            const btn = document.createElement('button');
            btn.className = 'btn-quitar btn-quitar-arbol';
            btn.dataset.clearBook = bookId;
            btn.title = 'Quitar valoración';
            btn.textContent = 'Quitar opinión';
            // Insertar después de la fila de estrellas
            starsRow.parentNode.insertBefore(btn, starsRow.nextSibling);
        }
    } else {
        btnExistente?.remove();
    }
}

// ══════════════════════════════════════════════════════════
// DELEGACIÓN DE CLICKS
// ══════════════════════════════════════════════════════════
document.addEventListener('click', e => {
    const clearBook = e.target.closest('[data-clear-book]');
    if (clearBook) {
        e.stopPropagation();
        // Poner a 0: llamar con el valor actual (toggle a 0 en rateBook)
        const id = clearBook.dataset.clearBook;
        misRatings[id] = misRatings[id] || 1; // garantiza que toggle lo lleve a 0
        rateBook(id, misRatings[id]);
        return;
    }

    const clearGenre = e.target.closest('[data-clear-genre]');
    if (clearGenre) {
        e.stopPropagation();
        const id = clearGenre.dataset.clearGenre;
        misGenreRatings[id] = misGenreRatings[id] || 1;
        rateGenre(id, misGenreRatings[id]);
        return;
    }

    const starLibro = e.target.closest('[data-star][data-id]:not([data-genre-id])');
    if (starLibro) {
        e.stopPropagation();
        rateBook(starLibro.dataset.id, parseInt(starLibro.dataset.star));
        return;
    }

    const starGenero = e.target.closest('[data-star][data-genre-id]');
    if (starGenero) {
        e.stopPropagation();
        rateGenre(starGenero.dataset.genreId, parseInt(starGenero.dataset.star));
    }
});

// ══════════════════════════════════════════════════════════
// ÁRBOL
// ══════════════════════════════════════════════════════════
function renderArbol(arbol) {
    const container = document.getElementById('tree-container');
    container.innerHTML = '';
    container.appendChild(mkNodo(arbol, 0));
    const firstRow = container.querySelector('.node-row');
    if (firstRow) firstRow.click();
}

function mkNodo(nodo, depth) {
    const wrapper = document.createElement('div');
    wrapper.dataset.id = nodo.id;

    const hijos      = [...(nodo.hijos || [])].sort((a, b) => b.valor - a.valor);
    const tieneHijos = hijos.length > 0;

    const row = document.createElement('div');
    row.className = 'node-row' + (tieneHijos ? '' : ' leaf');
    row.style.paddingLeft = (8 + depth * 4) + 'px';

    const icon = tieneHijos ? (depth === 0 ? '📚' : '📂') : '📖';
    const pm   = pesoEfectivo(nodo);
    const esPropio = tieneValoracionPropia(nodo);

    const prHtml = (mostrarPR && typeof nodo.valor === 'number')
        ? `<span class="node-pr">PR (${nodo.valor.toFixed(6)})</span>`
        : '';

    row.innerHTML = `
        <span class="arrow">▶</span>
        <span class="node-icon">${icon}</span>
        <span class="node-label">${escHtml(nodo.nombre)}</span>
        ${pm ? `<span class="node-peso${esPropio ? ' peso-propio' : ''}">★ (${pm.toFixed(2)})</span>` : ''}
        ${prHtml}`;

    wrapper.appendChild(row);

    if (tieneHijos) {
        wrapper.appendChild(mkGenreStars(nodo.id));

        const children = document.createElement('div');
        children.className = 'node-children';

        let loaded = false;
        let shown  = 0;

        const subCarpetas = hijos.filter(h => h.hijos?.length > 0);
        const hojas       = hijos.filter(h => !h.hijos?.length);
        const ordenado    = [...subCarpetas, ...hojas];

        function mostrarMas() {
            const hasta = Math.min(shown + PAGE_SIZE, ordenado.length);
            for (let i = shown; i < hasta; i++) children.appendChild(mkNodo(ordenado[i], depth + 1));
            shown = hasta;
            children.querySelector('.ver-mas-btn')?.remove();
            if (shown < ordenado.length) {
                const restantes = ordenado.length - shown;
                const btn = document.createElement('div');
                btn.className = 'ver-mas-btn';
                btn.style.paddingLeft = (8 + (depth + 1) * 4) + 'px';
                btn.textContent = `Ver ${Math.min(PAGE_SIZE, restantes)} más (${restantes} restantes)`;
                btn.addEventListener('click', e => { e.stopPropagation(); mostrarMas(); });
                children.appendChild(btn);
            }
        }

        row.addEventListener('click', () => {
            if (!loaded) { loaded = true; mostrarMas(); }
            const open = row.classList.toggle('open');
            children.classList.toggle('open', open);
        });

        wrapper.appendChild(children);

    } else {
        // Hoja: estrellas + botón ✕ si ya está valorado
        wrapper.appendChild(mkLeafStars(nodo.id));

        const myR = misRatings[nodo.id] || 0;
        if (myR > 0) {
            const btn = document.createElement('button');
            btn.className = 'btn-quitar btn-quitar-arbol';
            btn.dataset.clearBook = nodo.id;
            btn.title = 'Quitar valoración';
            btn.textContent = 'Quitar opinión';
            wrapper.appendChild(btn);
        }

        row.style.cursor = 'pointer';
        row.addEventListener('click', e => {
            e.stopPropagation();
            if (!e.target.closest('[data-star]') && !e.target.closest('.btn-quitar'))
                abrirPanelLibro(nodo);
        });
    }

    return wrapper;
}

// Estrellas hoja (libro)
function mkLeafStars(id) {
    const div = document.createElement('div');
    div.className  = 'leaf-stars-row';
    div.dataset.id = id;
    const v = misRatings[id] || 0;
    [1,2,3,4,5].forEach(s => {
        const star = document.createElement('span');
        star.className    = 'leaf-star' + (s <= v ? ' lit' : '');
        star.textContent  = '★';
        star.dataset.star = s;
        star.dataset.id   = id;
        div.appendChild(star);
    });
    return div;
}

// Estrellas nodo intermedio (género)
function mkGenreStars(id) {
    const div = document.createElement('div');
    div.className = 'genre-stars-row';
    div.dataset.genreId = id;
    const v = misGenreRatings[id] || 0;
    [1,2,3,4,5].forEach(s => {
        const star = document.createElement('span');
        star.className       = 'genre-star' + (s <= v ? ' lit' : '');
        star.textContent     = '★';
        star.dataset.star    = s;
        star.dataset.genreId = id;
        div.appendChild(star);
    });
    return div;
}

// ══════════════════════════════════════════════════════════
// BUSCADOR
// ══════════════════════════════════════════════════════════
let _searchTimer = null;

function debouncedSearch(value) {
    const clearBtn  = document.getElementById('search-clear');
    const treeEl    = document.getElementById('tree-container');
    const resultsEl = document.getElementById('search-results-container');
    const q = value.trim();
    clearTimeout(_searchTimer);
    if (!q) {
        clearBtn.classList.remove('visible');
        treeEl.style.display    = '';
        resultsEl.style.display = 'none';
        return;
    }
    clearBtn.classList.add('visible');
    treeEl.style.display    = 'none';
    resultsEl.style.display = '';
    _searchTimer = setTimeout(() => onSearch(value), 250);
}

function onSearch(value) {
    const q      = value.trim().toLowerCase();
    const listEl = document.getElementById('search-results-list');
    if (!q || !datosGlobales) return;
    listEl.innerHTML = '';

    const cats = [];
    function buscarCats(nodo, path) {
        if (esHoja(nodo)) return;
        if (nodo.nombre.toLowerCase().includes(q))
            cats.push({ ...nodo, _pathStr: path.slice(-2).join(' › ') });
        (nodo.hijos || []).forEach(h => buscarCats(h, [...path, nodo.nombre]));
    }
    buscarCats(datosGlobales.arbol, []);

    const hojasFilt = todasHojasFlat
        .filter(h => h.nombre.toLowerCase().includes(q))
        .slice(0, SEARCH_LIMIT);

    if (!cats.length && !hojasFilt.length) {
        listEl.innerHTML = `<div class="empty-state" style="padding:30px 10px"><div class="icon">🔍</div><p>Sin resultados para "<strong>${escHtml(q)}</strong>"</p></div>`;
        return;
    }

    const frag = document.createDocumentFragment();

    cats.forEach(cat => {
        const gRating  = misGenreRatings[cat.id] || 0;
        const pm       = pesoEfectivo(cat);
        const esPropio = tieneValoracionPropia(cat);
        const item     = document.createElement('div');
        item.className = 'search-result-item';
        item.innerHTML = `
            <span class="sri-icon">📂</span>
            <span class="sri-label">
                ${highlight(cat.nombre, q)}
                ${pm ? fmtPeso(pm, esPropio) : ''}
            </span>
            <div class="genre-stars-row" data-genre-id="${cat.id}" style="display:flex;gap:1px;flex-shrink:0">
                ${[1,2,3,4,5].map(s =>
                    `<span class="genre-star${s <= gRating ? ' lit' : ''}" data-star="${s}" data-genre-id="${cat.id}">★</span>`
                ).join('')}
            </div>`;
        frag.appendChild(item);
    });

    hojasFilt.forEach(libro => {
        const myR    = misRatings[libro.id] || 0;
        const pm     = myR > 0 ? myR : (libro.average_rating || 0);
        const esPropio = myR > 0;
        const item   = document.createElement('div');
        item.className = 'search-result-item';
        item.innerHTML = `
            <span class="sri-icon">📖</span>
            <span class="sri-label">
                ${highlight(libro.nombre, q)}
                ${pm ? fmtPeso(pm, esPropio) : ''}<br>
                <span style="font-size:0.7rem;color:var(--muted)">${escHtml(pathStr(libro))}</span>
            </span>
            <div class="sri-stars" data-id="${libro.id}">
                ${renderStars(libro.id, myR, 'sri-star')}
            </div>`;
        item.style.cursor = 'pointer';
        item.addEventListener('click', e => {
            if (!e.target.closest('[data-star]') && !e.target.closest('[data-genre-id]'))
                abrirPanelLibro(libro);
        });
        frag.appendChild(item);
    });

    const totalHojas = todasHojasFlat.filter(h => h.nombre.toLowerCase().includes(q)).length;
    if (totalHojas > SEARCH_LIMIT) {
        const aviso = document.createElement('div');
        aviso.style.cssText = 'text-align:center;font-size:0.75rem;color:var(--muted);padding:8px;';
        aviso.textContent = `Mostrando ${SEARCH_LIMIT} de ${totalHojas} resultados. Escribe más para afinar.`;
        frag.appendChild(aviso);
    }

    listEl.appendChild(frag);
}

function limpiarBusqueda() {
    const input = document.getElementById('search-input');
    input.value = '';
    debouncedSearch('');
    input.focus();
}

// ══════════════════════════════════════════════════════════
// PANEL DETALLE LIBRO
// ══════════════════════════════════════════════════════════
function abrirPanelLibro(libro) {
    // En modo debug el panel de detalle se ancla sobre el debug-panel
    // En modo normal, sobre el left-panel habitual
    const panelContenedor = typeof modoDebug !== 'undefined' && modoDebug 
        ? document.getElementById('debug-panel') 
        : document.querySelector('.left-panel');
        
    if (!panelContenedor) return;
    
    const panelAnterior = panelContenedor.querySelector('.book-detail-panel');
    if (panelAnterior) panelAnterior.remove();

    const titulo      = libro.title || libro.nombre || 'Título desconocido';
    const autores     = libro.authors || 'Autor desconocido'; //no se usa de momento porque autores no está en el dataset
    const descripcion = libro.descripcion || 'No hay sinopsis disponible para este libro.';
    const genero      = libro.genero || (libro.path ? pathStr(libro) : 'Sin categoría');
    const rating      = libro.average_rating ? `${libro.average_rating} / 5` : 'N/A';
    const votos       = libro.ratings_count ? `(${libro.ratings_count} votos)` : '';
    const paginas     = libro.num_pages ? `${libro.num_pages} págs.` : 'N/A';
    const anio        = libro.publication_year || 'N/A';
    const editorial   = libro.publisher || 'N/A';
    const isbn        = libro.isbn || 'N/A';

    // Mapeo de id a titulos
    let contadorSimilaresNoEncontrados = 0;
    let htmlSimilares = '';
    if (libro.tiene_similar && libro.similar_books?.length) {
        const nombresSimilares = libro.similar_books.map(idSimilar => {
            const libroEncontrado = todasHojasFlat.find(h => h.id === idSimilar);
            // Si lo encuentra devuelve el nombre
            if (libroEncontrado) {
                return libroEncontrado.nombre || libroEncontrado.title;
            }
            else {
                contadorSimilaresNoEncontrados++;
                return null;
            }
        }).filter(nombre => nombre !== null);

        // Aplicamos escHtml a cada nombre individualmente y unimos con salto de línea
        if (nombresSimilares.length > 0 || contadorSimilaresNoEncontrados > 0) {
        htmlSimilares = `
            <div class="info-similares"">
                <strong>Libros similares recomendados:</strong><br>
                <p>
                ${nombresSimilares.map(nombre => escHtml(nombre)).join('<br>')}
                </p>
                <p> Libros similares no disponibles en el dataset simplificado: ${contadorSimilaresNoEncontrados} </p>
            </div>`;
        }
    }

    const infoDiv = document.createElement('div');
    infoDiv.className = 'book-detail-panel';
    infoDiv.innerHTML = `
        <div class="detalles-libro">
            <div class="info-header">
                <h2 class="info-titulo">${escHtml(titulo)}</h2>
                <button id="btn-cerrar-info" class="btn-cerrar-simple">✕</button>
            </div>
            <div class="info-badges">
                <span class="badge badge-genero">🏷️ ${escHtml(genero)}</span>
                <span class="badge badge-rating">⭐ ${escHtml(rating)} <small>${escHtml(votos)}</small></span>
            </div>
            <div class="info-sinopsis">
                <h3>Sinopsis</h3>
                <p>${escHtml(descripcion)}</p>
            </div>
            <div class="info-metadata">
                <div><strong>Páginas:</strong> ${escHtml(paginas)}</div>
                <div><strong>Año:</strong> ${escHtml(anio)}</div>
                <div><strong>Editorial:</strong> ${escHtml(editorial)}</div>
                <div><strong>ISBN:</strong> ${escHtml(isbn)}</div>
            </div>
        </div>
        ${htmlSimilares}
    `;

    panelContenedor.appendChild(infoDiv);
    document.getElementById('btn-cerrar-info').addEventListener('click', () => infoDiv.remove());
}