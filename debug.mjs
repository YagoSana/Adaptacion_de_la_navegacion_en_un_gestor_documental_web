// ══════════════════════════════════════════════════════════
// MODO DEBUG — Árbol con PageRank visible e interacción completa
//
// Muestra un árbol independiente donde:
//   · Cada nodo expone su valor de PageRank en notación científica
//   · Las hojas muestran además su average_rating del dataset
//   · Por subcategoría se limita a los 10 libros con mayor average_rating
//   · Se pueden valorar libros y géneros igual que en el árbol normal
//   · Se puede abrir el panel de detalle de cada libro
// ══════════════════════════════════════════════════════════

import { esHoja, escHtml, pathStr } from './utils.mjs';

const MAX_POR_SUBCAT = 10;

// ── Referencia a callbacks inyectados desde app.mjs ──────
let _callbacks = null;

// ── Clona el árbol recortando hojas por average_rating ────
function clonarConLimite(nodo) {
    if (esHoja(nodo)) return { ...nodo };

    const hijosClonados  = (nodo.hijos || []).map(clonarConLimite);
    const subCarpetas    = hijosClonados.filter(h => !esHoja(h));
    const hojas          = hijosClonados.filter(h => esHoja(h));

    // Dentro de cada nodo-hoja directo: top MAX_POR_SUBCAT por average_rating
    const hojasLimitadas = hojas
        .slice()
        .sort((a, b) => (b.average_rating || 0) - (a.average_rating || 0))
        .slice(0, MAX_POR_SUBCAT);

    // Para sub-carpetas, aplicar el límite en sus propias hojas
    const subCarpetasLimitadas = subCarpetas.map(sc => {
        const hijosHoja   = (sc.hijos || []).filter(h => esHoja(h));
        const hijosNoHoja = (sc.hijos || []).filter(h => !esHoja(h));
        const limitados   = hijosHoja
            .slice()
            .sort((a, b) => (b.average_rating || 0) - (a.average_rating || 0))
            .slice(0, MAX_POR_SUBCAT);
        return { ...sc, hijos: [...hijosNoHoja, ...limitados] };
    });

    return { ...nodo, hijos: [...subCarpetasLimitadas, ...hojasLimitadas] };
}

// ── Punto de entrada: renderiza el árbol debug en su contenedor ──
// callbacks = { misRatings, misGenreRatings, pesoEfectivo, tieneValoracionPropia,
//               rateBook, rateGenre, abrirPanelLibro }
export function renderArbolDebug(arbol, callbacks) {
    _callbacks = callbacks;
    const container = document.getElementById('debug-tree-container');
    if (!container) return;
    const debugArbol = clonarConLimite(arbol);
    container.innerHTML = '';
    container.appendChild(mkNodoDebug(debugArbol, 0));
    const firstRow = container.querySelector('.node-row');
    if (firstRow) firstRow.click();
}

// ── Actualiza estrellas de un libro en el árbol debug ────
export function actualizarEstrellaDebugLibro(bookId, valor) {
    const container = document.getElementById('debug-tree-container');
    if (!container) return;

    // Estrellas hoja
    container.querySelectorAll(`.dbg-leaf-stars[data-id="${bookId}"] .dbg-leaf-star`).forEach(s =>
        s.classList.toggle('lit', parseInt(s.dataset.star) <= valor));

    // Peso en la fila
    _actualizarPesoFilaDebug(container, bookId);

    // Botón quitar
    _actualizarBtnQuitarDebug(container, bookId, valor);
}

// ── Actualiza estrellas de un género en el árbol debug ───
export function actualizarEstrellaDebugGenero(genreId, valor) {
    const container = document.getElementById('debug-tree-container');
    if (!container) return;
    container.querySelectorAll(`.dbg-genre-stars[data-genre-id="${genreId}"] .dbg-genre-star`).forEach(s =>
        s.classList.toggle('lit', parseInt(s.dataset.star) <= valor));
}

// ── Actualiza el badge de peso en la fila de un libro ────
function _actualizarPesoFilaDebug(container, bookId) {
    if (!_callbacks) return;
    const wrapper = container.querySelector(`[data-id="${bookId}"]`);
    if (!wrapper) return;
    const row = wrapper.querySelector('.node-row');
    if (!row) return;
    const { misRatings, pesoEfectivo } = _callbacks;

    // Reconstruir hoja mínima para pesoEfectivo
    const hoja = { id: bookId, hijos: [] };
    const myR  = misRatings[bookId] || 0;
    const pm   = myR > 0 ? myR : (wrapper._avgRating || 0);

    let pesoEl = row.querySelector('.node-peso');
    if (!pesoEl) { pesoEl = document.createElement('span'); row.insertBefore(pesoEl, row.querySelector('.dbg-avg') || row.querySelector('.dbg-pr')); }
    pesoEl.className   = `node-peso${myR > 0 ? ' peso-propio' : ''}`;
    pesoEl.textContent = pm ? `★ (${pm.toFixed(2)})` : '';
}

// ── Muestra/oculta el botón quitar en el árbol debug ─────
function _actualizarBtnQuitarDebug(container, bookId, rating) {
    const wrapper  = container.querySelector(`[data-id="${bookId}"]`);
    if (!wrapper) return;
    const starsRow = wrapper.querySelector('.dbg-leaf-stars');
    if (!starsRow) return;
    let btnEx = wrapper.querySelector('.dbg-btn-quitar');
    if (rating > 0) {
        if (!btnEx) {
            const btn = document.createElement('button');
            btn.className        = 'btn-quitar btn-quitar-arbol dbg-btn-quitar';
            btn.dataset.clearBook = bookId;
            btn.title            = 'Quitar valoración';
            btn.textContent      = 'Quitar opinión';
            starsRow.parentNode.insertBefore(btn, starsRow.nextSibling);
        }
    } else {
        btnEx?.remove();
    }
}

// ── Construye un nodo del árbol debug ────────────────────
function mkNodoDebug(nodo, depth) {
    const wrapper = document.createElement('div');
    wrapper.dataset.id = nodo.id;
    // Guardamos average_rating para poder recuperarlo al actualizar pesos
    if (esHoja(nodo)) wrapper._avgRating = nodo.average_rating || 0;

    // Hijos: todos ordenados por PageRank (que ya refleja las valoraciones del usuario)
    const hijos      = [...(nodo.hijos || [])].sort((a, b) => (b.valor || 0) - (a.valor || 0));
    const tieneHijos = hijos.length > 0;

    const row = document.createElement('div');
    row.className = 'node-row' + (tieneHijos ? '' : ' leaf');
    row.style.paddingLeft = (8 + depth * 4) + 'px';

    const icon = tieneHijos ? (depth === 0 ? '📚' : '📂') : '📖';

    // En debug, el peso solo se muestra si el propio usuario ha valorado algo
    // (no usamos average_rating del dataset para no contaminar la visualización del PageRank)
    const { misRatings, misGenreRatings, pesoEfectivo, tieneValoracionPropia } = _callbacks;
    const esPropio = tieneValoracionPropia(nodo);
    const pm       = esPropio ? pesoEfectivo(nodo) : 0;
    const pesoHtml = (esPropio && pm)
        ? `<span class="node-peso peso-propio">★ (${pm.toFixed(2)})</span>`
        : '';

    const prTag = `<span class="dbg-pr" title="PageRank">${nodo.valor?.toExponential(3) ?? '—'}</span>`;

    row.innerHTML = `
        <span class="arrow">▶</span>
        <span class="node-icon">${icon}</span>
        <span class="node-label">${escHtml(nodo.nombre)}</span>
        ${pesoHtml}
        ${prTag}`;

    wrapper.appendChild(row);

    if (tieneHijos) {
        // Estrellas de género/subgénero
        wrapper.appendChild(mkDebugGenreStars(nodo.id));

        const children = document.createElement('div');
        children.className = 'node-children';
        let loaded = false;
        let shown  = 0;

        function mostrarMas() {
            const hasta = Math.min(shown + MAX_POR_SUBCAT, hijos.length);
            for (let i = shown; i < hasta; i++) children.appendChild(mkNodoDebug(hijos[i], depth + 1));
            shown = hasta;
            children.querySelector('.ver-mas-btn')?.remove();
            if (shown < hijos.length) {
                const restantes = hijos.length - shown;
                const btn = document.createElement('div');
                btn.className = 'ver-mas-btn';
                btn.style.paddingLeft = (8 + (depth + 1) * 4) + 'px';
                btn.textContent = `Ver ${Math.min(MAX_POR_SUBCAT, restantes)} más (${restantes} restantes)`;
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
        // Hoja: estrellas de libro + botón quitar si ya valorado
        wrapper.appendChild(mkDebugLeafStars(nodo.id));

        const myR = misRatings[nodo.id] || 0;
        if (myR > 0) {
            const btn = document.createElement('button');
            btn.className        = 'btn-quitar btn-quitar-arbol dbg-btn-quitar';
            btn.dataset.clearBook = nodo.id;
            btn.title            = 'Quitar valoración';
            btn.textContent      = 'Quitar opinión';
            wrapper.appendChild(btn);
        }

        row.style.cursor = 'pointer';
        row.addEventListener('click', e => {
            e.stopPropagation();
            if (!e.target.closest('[data-star]') && !e.target.closest('.btn-quitar'))
                _callbacks.abrirPanelLibro(nodo);
        });
    }

    return wrapper;
}

// ── Estrellas de libro (hoja) en debug ───────────────────
function mkDebugLeafStars(id) {
    const div = document.createElement('div');
    div.className  = 'dbg-leaf-stars leaf-stars-row';
    div.dataset.id = id;
    const v = (_callbacks?.misRatings[id] || 0);
    [1,2,3,4,5].forEach(s => {
        const star = document.createElement('span');
        star.className    = 'dbg-leaf-star leaf-star' + (s <= v ? ' lit' : '');
        star.textContent  = '★';
        star.dataset.star = s;
        star.dataset.id   = id;
        div.appendChild(star);
    });
    return div;
}

// ── Estrellas de género/subgénero en debug ───────────────
function mkDebugGenreStars(id) {
    const div = document.createElement('div');
    div.className       = 'dbg-genre-stars genre-stars-row';
    div.dataset.genreId = id;
    const v = (_callbacks?.misGenreRatings[id] || 0);
    [1,2,3,4,5].forEach(s => {
        const star = document.createElement('span');
        star.className       = 'dbg-genre-star genre-star' + (s <= v ? ' lit' : '');
        star.textContent     = '★';
        star.dataset.star    = s;
        star.dataset.genreId = id;
        div.appendChild(star);
    });
    return div;
}
