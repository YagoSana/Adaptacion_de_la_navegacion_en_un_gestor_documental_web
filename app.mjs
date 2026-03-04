// ══════════════════════════════════════════════════════════
// ESTADO GLOBAL
// ══════════════════════════════════════════════════════════
let datosGlobales  = null;
let todasHojasFlat = [];  // [{ id, nombre, valor, path[] }]
let similarMap     = {};  // { book_id: [similar_id, ...] }
let misRatings     = {};

try {
    misRatings = JSON.parse(localStorage.getItem('bookrank_ratings') || '{}');
} catch (e) {}

const PAGE_SIZE    = 10;
const SEARCH_LIMIT = 50;

// ══════════════════════════════════════════════════════════
// INIT — conectar eventos al cargar el DOM
// ══════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
    // Botón calcular
    document.getElementById('btn-calc').addEventListener('click', calcular);

    // Sliders → actualizar etiquetas
    document.getElementById('input_libros').addEventListener('input', e => {
        document.getElementById('lbl_libros').textContent = e.target.value;
    });
    document.getElementById('input_refs').addEventListener('input', e => {
        document.getElementById('lbl_refs').textContent = e.target.value;
    });

    // Tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab, btn));
    });

    // Buscador
    document.getElementById('search-input').addEventListener('input', e => {
        debouncedSearch(e.target.value);
    });
    document.getElementById('search-clear').addEventListener('click', limpiarBusqueda);
});

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
// CALCULAR
// ══════════════════════════════════════════════════════════
async function calcular() {
    const btn     = document.getElementById('btn-calc');
    const overlay = document.getElementById('overlay');

    btn.disabled    = true;
    btn.textContent = 'Calculando…';
    overlay.classList.add('show');

    try {
        const res = await fetch('http://localhost:8080', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                peso_libro:      parseFloat(document.getElementById('input_libros').value),
                peso_referencia: parseFloat(document.getElementById('input_refs').value)
            })
        });

        datosGlobales = await res.json();
        if (datosGlobales.similar_map) similarMap = datosGlobales.similar_map;

        todasHojasFlat = [];
        recogerHojas(datosGlobales.arbol, todasHojasFlat, []);
        todasHojasFlat.sort((a, b) => b.valor - a.valor);

        renderPopular();
        renderPersonal();
        renderRecomendaciones();
        renderArbol(datosGlobales.arbol);
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
function esHoja(n) {
    return !n.hijos || n.hijos.length === 0;
}

function recogerHojas(nodo, acc, path) {
    if (esHoja(nodo)) {
        acc.push({ ...nodo, path: [...path] });
        return;
    }
    (nodo.hijos || []).forEach(h => recogerHojas(h, acc, [...path, nodo.nombre]));
}

function pathStr(hoja) {
    return (hoja.path || []).slice(-2).join(' › ');
}

function escHtml(s) {
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function highlight(text, q) {
    const safeQ = q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return escHtml(text).replace(new RegExp(`(${safeQ})`, 'gi'), '<span class="highlight">$1</span>');
}

function renderStars(id, rating, cssClass) {
    return [1, 2, 3, 4, 5].map(s =>
        `<span class="${cssClass} ${s <= rating ? 'lit' : ''}" data-star="${s}" data-id="${id}">★</span>`
    ).join('');
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
// RENDER — PERSONAL
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

    const scored = ratedIds
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

    const hojaMap  = Object.fromEntries(todasHojasFlat.map(h => [h.id, h]));
    const ratedSet = new Set(ratedIds);
    const candidatos = {};

    // Via similar_map si existe
    if (Object.keys(similarMap).length) {
        ratedIds.forEach(id => {
            const myR = misRatings[id] || 0;
            (similarMap[id] || []).forEach(sid => {
                if (!ratedSet.has(sid) && hojaMap[sid])
                    candidatos[sid] = (candidatos[sid] || 0) + myR * hojaMap[sid].valor;
            });
        });
    }

    // Fallback: mismo género (último elemento del path)
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
    const card   = document.createElement('div');
    card.className   = 'book-card';
    card.dataset.id  = libro.id;

    const rating  = misRatings[libro.id] || 0;
    const genHtml = showGenre ? `<span class="book-genre">${escHtml(pathStr(libro))}</span>` : '';
    const myRatingHtml = (showMyRating && rating > 0)
        ? `<div class="my-rating-label">Tu valoración: ${rating}/5</div>`
        : '';

    card.innerHTML = `
        <div class="book-rank">${rank}</div>
        <div class="book-info">
            <div class="book-title">${escHtml(libro.nombre)}</div>
            ${genHtml}
            <div class="stars-wrap" data-id="${libro.id}">
                ${renderStars(libro.id, rating, 'star')}
            </div>
            ${myRatingHtml}
        </div>`;
    card.style.cursor = 'pointer';
    card.addEventListener('click', (e) => {
        if (!e.target.closest('[data-star]')) {
            abrirPanelLibro(libro);
        }
    });
    return card;
}

function mkCardRec(libro, rank) {
    const card  = document.createElement('div');
    card.className  = 'book-card rec';
    card.dataset.id = libro.id;

    const rating = misRatings[libro.id] || 0;

    card.innerHTML = `
        <div class="book-rank rec-icon">✦</div>
        <div class="book-info">
            <div class="book-title">${escHtml(libro.nombre)}</div>
            <span class="book-genre">${escHtml(pathStr(libro))}</span>
            <div class="stars-wrap" data-id="${libro.id}">
                ${renderStars(libro.id, rating, 'star')}
            </div>
        </div>`;

    card.style.cursor = 'pointer';
    card.addEventListener('click', (e) => {
        if (!e.target.closest('[data-star]')) {
            abrirPanelLibro(libro);
        }
    });
    return card;
}

// ══════════════════════════════════════════════════════════
// RATING
// ══════════════════════════════════════════════════════════
function rateBook(id, stars) {
    misRatings[id] = (misRatings[id] === stars) ? 0 : stars;
    try { localStorage.setItem('bookrank_ratings', JSON.stringify(misRatings)); } catch (e) {}

    const v = misRatings[id];

    // Actualizar todas las instancias de estrellas en el DOM
    document.querySelectorAll(`.stars-wrap[data-id="${id}"] .star`).forEach(s => {
        s.classList.toggle('lit', parseInt(s.dataset.star) <= v);
    });
    document.querySelectorAll(`.leaf-stars-row[data-id="${id}"] .leaf-star`).forEach(s => {
        s.classList.toggle('lit', parseInt(s.dataset.star) <= v);
    });
    document.querySelectorAll(`.sri-stars[data-id="${id}"] .sri-star`).forEach(s => {
        s.classList.toggle('lit', parseInt(s.dataset.star) <= v);
    });

    renderPersonal();
    renderRecomendaciones();
}

// Delegación de eventos para estrellas (en vez de onclick inline)
document.addEventListener('click', e => {
    const star = e.target.closest('[data-star][data-id]');
    if (!star) return;
    e.stopPropagation();
    rateBook(star.dataset.id, parseInt(star.dataset.star));
});

// ══════════════════════════════════════════════════════════
// ÁRBOL
// ══════════════════════════════════════════════════════════
function renderArbol(arbol) {
    const container = document.getElementById('tree-container');
    container.innerHTML = '';
    container.appendChild(mkNodo(arbol, 0));

    // Expandir la raíz automáticamente
    const firstRow = container.querySelector('.node-row');
    if (firstRow) firstRow.click();
}

function mkNodo(nodo, depth) {
    const wrapper    = document.createElement('div');
    wrapper.dataset.id = nodo.id;

    const hijos      = [...(nodo.hijos || [])].sort((a, b) => b.valor - a.valor);
    const tieneHijos = hijos.length > 0;

    const row = document.createElement('div');
    row.className = 'node-row' + (tieneHijos ? '' : ' leaf');
    row.style.paddingLeft = (8 + depth * 4) + 'px';

    const icon = tieneHijos
        ? (depth === 0 ? '📚' : depth === 1 ? '📂' : '🏷️')
        : '📖';

    row.innerHTML = `
        <span class="arrow">▶</span>
        <span class="node-icon">${icon}</span>
        <span class="node-label">${escHtml(nodo.nombre)}</span>`;

    wrapper.appendChild(row);

    if (tieneHijos) {
        const children = document.createElement('div');
        children.className = 'node-children';

        let loaded = false;
        let shown  = 0;

        // Subcarpetas primero, luego hojas (paginadas)
        const subCarpetas = hijos.filter(h => h.hijos?.length > 0);
        const hojas       = hijos.filter(h => !h.hijos?.length);
        const ordenado    = [...subCarpetas, ...hojas];

        function mostrarMas() {
            const hasta = Math.min(shown + PAGE_SIZE, ordenado.length);
            for (let i = shown; i < hasta; i++) {
                children.appendChild(mkNodo(ordenado[i], depth + 1));
            }
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
        wrapper.appendChild(mkLeafStars(nodo.id));
        
        // Annadimos cursor pointer para indicar que es clickeable
        row.style.cursor = 'pointer'; 
        
        row.addEventListener('click', e => {
            e.stopPropagation();
            // Evitamos abrir el panel si el usuario hizo clic en una estrella para valorar
            if (!e.target.closest('[data-star]')) {
                abrirPanelLibro(nodo);
            }
        });
    }

    return wrapper;
}

function mkLeafStars(id) {
    const div   = document.createElement('div');
    div.className   = 'leaf-stars-row';
    div.dataset.id  = id;

    const v = misRatings[id] || 0;
    [1, 2, 3, 4, 5].forEach(s => {
        const star = document.createElement('span');
        star.className   = 'leaf-star' + (s <= v ? ' lit' : '');
        star.textContent = '★';
        star.dataset.star = s;
        star.dataset.id   = id;
        div.appendChild(star);
    });

    return div;
}

// ══════════════════════════════════════════════════════════
// BUSCADOR
// ══════════════════════════════════════════════════════════
let _searchTimer = null;

function debouncedSearch(value) {
    const clearBtn   = document.getElementById('search-clear');
    const treeEl     = document.getElementById('tree-container');
    const resultsEl  = document.getElementById('search-results-container');
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
    const q     = value.trim().toLowerCase();
    const listEl = document.getElementById('search-results-list');

    if (!q || !datosGlobales) return;
    listEl.innerHTML = '';

    // Categorías coincidentes
    const cats = [];
    function buscarCats(nodo, path) {
        if (esHoja(nodo)) return;
        if (nodo.nombre.toLowerCase().includes(q))
            cats.push({ ...nodo, _pathStr: path.slice(-2).join(' › ') });
        (nodo.hijos || []).forEach(h => buscarCats(h, [...path, nodo.nombre]));
    }
    buscarCats(datosGlobales.arbol, []);

    // Hojas coincidentes (ya ordenadas, limitadas)
    const hojasFilt = todasHojasFlat
        .filter(h => h.nombre.toLowerCase().includes(q))
        .slice(0, SEARCH_LIMIT);

    if (!cats.length && !hojasFilt.length) {
        listEl.innerHTML = `<div class="empty-state" style="padding:30px 10px"><div class="icon">🔍</div><p>Sin resultados para "<strong>${escHtml(q)}</strong>"</p></div>`;
        return;
    }

    const frag = document.createDocumentFragment();

    cats.forEach(cat => {
        const item = document.createElement('div');
        item.className = 'search-result-item';
        item.innerHTML = `<span class="sri-icon">📂</span><span class="sri-label">${highlight(cat.nombre, q)}</span>`;
        frag.appendChild(item);
    });

    hojasFilt.forEach(libro => {
        const rating = misRatings[libro.id] || 0;
        const item   = document.createElement('div');
        item.className = 'search-result-item';
        item.innerHTML = `
            <span class="sri-icon">📖</span>
            <span class="sri-label">
                ${highlight(libro.nombre, q)}<br>
                <span style="font-size:0.7rem;color:var(--muted)">${escHtml(pathStr(libro))}</span>
            </span>
            <div class="sri-stars" data-id="${libro.id}">
                ${renderStars(libro.id, rating, 'sri-star')}
            </div>`;
        item.style.cursor = 'pointer';
        item.addEventListener('click', (e) => {
            if (!e.target.closest('[data-star]')) {
                abrirPanelLibro(libro);
            }
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
// PANEL LATERAL
// ══════════════════════════════════════════════════════════
function abrirPanelLibro(libro) {

    const panelContenedor = document.querySelector('.left-panel'); 
    if (!panelContenedor) return;

    // Si ya había un panel de un libro abierto, lo eliminamos para que no se acumulen
    const panelAnterior = panelContenedor.querySelector('.book-detail-panel');
    if (panelAnterior) panelAnterior.remove();

    // Preparar los datos
    const titulo      = libro.title || libro.nombre || 'Título desconocido';
    const autores     = libro.authors ? libro.authors : 'Autor desconocido';
    const descripcion = libro.descripcion || 'No hay sinopsis disponible para este libro.';
    const genero      = libro.genero || (libro.path ? pathStr(libro) : 'Sin categoría');
    const rating      = libro.average_rating ? `${libro.average_rating} / 5` : 'N/A';
    const votos       = libro.ratings_count ? `(${libro.ratings_count} votos)` : '';
    const paginas     = libro.num_pages ? `${libro.num_pages} págs.` : 'N/A';
    const anio        = libro.publication_year || 'N/A';
    const editorial   = libro.publisher || 'N/A';
    const isbn        = libro.isbn || 'N/A';

    // Crear tercera ventana flotante
    const infoDiv = document.createElement('div');
    infoDiv.className = 'book-detail-panel';
    
    infoDiv.innerHTML = `
        <div class="detalles-libro">
            <div class="info-header">
                <h2 class="info-titulo">${escHtml(titulo)}</h2>
                <button id="btn-cerrar-info" class="btn-cerrar-simple">✕</button>
            </div>
            <!--
            <p class="info-autores"><strong>${escHtml(autores)}</strong></p>
            -->
            
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
        
        ${libro.tiene_similar && libro.similar_books && libro.similar_books.length > 0 ? `
            <div class="info-similares">
                <strong>Libros similares recomendados (IDs):</strong> 
                ${escHtml(libro.similar_books.join(', '))}
            </div>
        ` : ''}
    `;

    // Poner en panel izquierdo
    panelContenedor.appendChild(infoDiv);

    // Acción del botón X: destruye el div
    document.getElementById('btn-cerrar-info').addEventListener('click', () => {
        infoDiv.remove();
    });
}