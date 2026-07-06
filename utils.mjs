// ==========================================================
// UTILIDADES COMPARTIDAS
// ==========================================================

export function esHoja(n) { return !n.hijos || n.hijos.length === 0; }

export function recogerHojas(nodo, acc, path) {
    if (esHoja(nodo)) { acc.push({ ...nodo, path: [...path] }); return; }
    (nodo.hijos || []).forEach(h => recogerHojas(h, acc, [...path, nodo.nombre]));
}

export function pathStr(hoja) { return (hoja.path || []).slice(-2).join(' › '); }

export function escHtml(s) {
    return String(s)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;')
        .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

export function highlight(text, q) {
    const safeQ = q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return escHtml(text).replace(new RegExp(`(${safeQ})`, 'gi'), '<span class="highlight">$1</span>');
}

export function renderStars(id, rating, cssClass) {
    return [1,2,3,4,5].map(s =>
        `<span class="${cssClass} ${s <= rating ? 'lit' : ''}" data-star="${s}" data-id="${id}">★</span>`
    ).join('');
}
