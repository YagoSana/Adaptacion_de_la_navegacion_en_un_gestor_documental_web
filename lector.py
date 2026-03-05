import json
import networkx as nx

# Jerarquía fija: qué géneros pertenecen a qué categoría intermedia
JERARQUIA = {
    "Historical fiction": {
        "padre": "Fiction",
        "subgrupo": "Historical fiction"
    },
    "Historical mystery": {
        "padre": "Fiction",
        "subgrupo": "Historical fiction"
    },
    "Christian Historical Fiction": {
        "padre": "Fiction",
        "subgrupo": "Historical fiction"
    },
    "Biographical": {
        "padre": "Fiction",
        "subgrupo": "Historical fiction"
    },
    "Alternate history": {
        "padre": "Fiction",
        "subgrupo": "Historical fiction"
    },
    "Historical adventure": {
        "padre": "Fiction",
        "subgrupo": "Historical fiction"
    },
    "Detective crime": {
        "padre": "Fiction",
        "subgrupo": "Mystery&Crime fiction/Crime"
    },
    "Noir crime": {
        "padre": "Fiction",
        "subgrupo": "Mystery&Crime fiction/Crime"
    },
    "Hard boiled crime": {
        "padre": "Fiction",
        "subgrupo": "Mystery&Crime fiction/Crime"
    },
    "Generic crime": {
        "padre": "Fiction",
        "subgrupo": "Mystery&Crime fiction/Crime"
    },
    "Cozy mystery": {
        "padre": "Fiction",
        "subgrupo": "Mystery&Crime fiction/Mystery"
    },
    "Murder mystery": {
        "padre": "Fiction",
        "subgrupo": "Mystery&Crime fiction/Mystery"
    },
    "Paranormal mystery": {
        "padre": "Fiction",
        "subgrupo": "Mystery&Crime fiction/Mystery"
    },
    "Generic mystery": {
       "padre": "Fiction",
        "subgrupo": "Mystery&Crime fiction/Mystery"
    },
    "Psychological thriller": {
        "padre": "Fiction",
        "subgrupo": "Mystery&Crime fiction/Thriller"
    },
    "Spy thriller": {
        "padre": "Fiction",
        "subgrupo": "Mystery&Crime fiction/Thriller"
    },
    "Legal thriller": {
        "padre": "Fiction",
        "subgrupo": "Mystery&Crime fiction/Thriller"
    },
    "Medical thriller": {
        "padre": "Fiction",
        "subgrupo": "Mystery&Crime fiction/Thriller"
    },
    "Supernatural thriller": {
        "padre": "Fiction",
        "subgrupo": "Mystery&Crime fiction/Thriller"
    },
    "Mystery thriller": {
        "padre": "Fiction",
        "subgrupo": "Mystery&Crime fiction/Thriller"
    },
    "Generic thriller": {
        "padre": "Fiction",
        "subgrupo": "Mystery&Crime fiction/Thriller"
    },
    "Love-inspired suspense": {
        "padre": "Fiction",
        "subgrupo": "Mystery&Crime fiction/Suspense"
    },
    "Generic suspense": {
        "padre": "Fiction",
        "subgrupo": "Mystery&Crime fiction/Suspense"
    },
}

# Árbol de nodos intermedios con sus niveles
NODOS_FIJOS = {
    "Fiction":                      0,
    "Historical fiction":           1,
    "Mystery&Crime fiction":        1,
    "Mystery&Crime fiction/Crime":      2,
    "Mystery&Crime fiction/Mystery":    2,
    "Mystery&Crime fiction/Thriller":   2,
    "Mystery&Crime fiction/Suspense":   2,
}

# Nombres legibles para los nodos intermedios (lo que se muestra)
NOMBRE_LEGIBLE = {
    "Mystery&Crime fiction/Crime":    "Crime",
    "Mystery&Crime fiction/Mystery":  "Mystery",
    "Mystery&Crime fiction/Thriller": "Thriller",
    "Mystery&Crime fiction/Suspense": "Suspense",
}


def leer_entrada(ruta_json):
    """
    Construye el grafo jerárquico desde el dataset JSON.
    Nodos: Fiction > subgrupo > género > libro (book_id como nodo, título como atributo)
    """
    G = nx.DiGraph()

    # 1. Añadir nodos fijos del árbol
    for nodo, nivel in NODOS_FIJOS.items():
        nombre_display = NOMBRE_LEGIBLE.get(nodo, nodo)
        G.add_node(nodo, nivel=nivel, display=nombre_display)

    # Conectar nodos fijos
    G.add_edge("Fiction", "Historical fiction")
    G.add_edge("Fiction", "Mystery&Crime fiction")
    G.add_edge("Mystery&Crime fiction", "Mystery&Crime fiction/Crime")
    G.add_edge("Mystery&Crime fiction", "Mystery&Crime fiction/Mystery")
    G.add_edge("Mystery&Crime fiction", "Mystery&Crime fiction/Thriller")
    G.add_edge("Mystery&Crime fiction", "Mystery&Crime fiction/Suspense")

    # 2. Leer el dataset
    with open(ruta_json, 'r', encoding='utf-8') as f:
        libros = json.load(f)

    # ── Deduplicación en dos pasos ────────────────────────────────────────────
    # Paso A: por book_id — quedarse con el que tenga mayor ratings_count
    por_id = {}
    for libro in libros:
        bid = libro.get("book_id")
        if not bid:
            continue
        rc_nuevo = int(libro.get("ratings_count") or 0)
        if bid not in por_id or rc_nuevo > int(por_id[bid].get("ratings_count") or 0):
            por_id[bid] = libro

    # Paso B: por título normalizado — si dos book_ids distintos tienen el mismo
    # título (ignorando mayúsculas, espacios y puntuación), conservar el de mayor
    # ratings_count y redirigir el id descartado al ganador.
    import unicodedata, re

    def normalizar_titulo(t):
        if not t:
            return ""
        t = t.lower().strip()
        t = unicodedata.normalize("NFKD", t)
        t = t.encode("ascii", "ignore").decode("ascii")
        t = re.sub(r"[^a-z0-9 ]", "", t)
        t = re.sub(r"\s+", " ", t).strip()
        return t

    titulo_a_id = {}        # titulo_normalizado -> book_id ganador
    id_redirigido = {}      # book_id descartado -> book_id ganador

    for bid, libro in list(por_id.items()):
        titulo_norm = normalizar_titulo(libro.get("title", ""))
        if not titulo_norm:
            continue
        if titulo_norm not in titulo_a_id:
            titulo_a_id[titulo_norm] = bid
        else:
            ganador_id = titulo_a_id[titulo_norm]
            rc_actual  = int(por_id[ganador_id].get("ratings_count") or 0)
            rc_nuevo   = int(libro.get("ratings_count") or 0)
            if rc_nuevo > rc_actual:
                # El nuevo gana: el anterior queda descartado
                id_redirigido[ganador_id] = bid
                titulo_a_id[titulo_norm] = bid
            else:
                # El anterior sigue ganando: el nuevo queda descartado
                id_redirigido[bid] = ganador_id
                del por_id[bid]   # eliminar duplicado del índice

    # Eliminar del índice los ids que perdieron
    for bid_desc in id_redirigido:
        por_id.pop(bid_desc, None)

    libros_unicos = list(por_id.values())

    dup_id    = len(libros) - len({l["book_id"] for l in libros if l.get("book_id")})
    dup_titulo = len({l["book_id"] for l in libros if l.get("book_id")}) - len(libros_unicos)
    print(f"[lector] Duplicados por book_id eliminados:  {dup_id}")
    print(f"[lector] Duplicados por título eliminados:   {dup_titulo}")
    print(f"[lector] Libros únicos tras deduplicación:   {len(libros_unicos)}")
    # ─────────────────────────────────────────────────────────────────────────

    # Índice book_id -> libro (para resolver similar_books después)
    # Incluye redirecciones para que referencias a ids descartados sigan funcionando
    indice = {l["book_id"]: l for l in libros_unicos}
    for desc, ganador in id_redirigido.items():
        if ganador in indice:
            indice[desc] = indice[ganador]   # redirigir referencias

    nodos_genero_añadidos = set()
    referencias = []

    for libro in libros_unicos:
        genero = libro.get("genero")
        book_id = libro.get("book_id")
        title = libro.get("title", f"Libro {book_id}")

        if not genero or not book_id:
            continue

        info = JERARQUIA.get(genero)
        if not info:
            continue

        subgrupo = info["subgrupo"]

        # Añadir nodo de género si no existe aún (nivel 2 o 3 según caso)
        nivel_genero = 2 if subgrupo == "Historical fiction" else 3
        if genero not in nodos_genero_añadidos:
            G.add_node(genero, nivel=nivel_genero, display=genero)
            G.add_edge(subgrupo, genero)
            nodos_genero_añadidos.add(genero)

        # Añadir nodo libro (nivel hoja) — book_id garantizado único
        nivel_libro = nivel_genero + 1
        G.add_node(book_id,
                   nivel=nivel_libro,
                   display=title,
                   title=title,
                   genero=genero,
                   average_rating=float(libro.get("average_rating") or 0),
                   ratings_count=int(libro.get("ratings_count") or 0),
                   authors=libro.get("authors"),
                   descripcion=libro.get("descripcion"),
                   publisher=libro.get("publisher"),
                   num_pages=libro.get("num_pages"),
                   publication_year=libro.get("publication_year"),
                   isbn=libro.get("isbn"),
                   similar_books=libro.get("similar_books", []),
                   tiene_similar=len(libro.get("similar_books", [])) > 0)
        G.add_edge(genero, book_id)

        # Recopilar referencias (similar_books dentro del dataset),
        # resolviendo redirecciones de ids descartados
        for similar_id in libro.get("similar_books", []):
            similar_id_real = id_redirigido.get(similar_id, similar_id)
            if similar_id_real in indice and similar_id_real != book_id:
                referencias.append((book_id, similar_id_real))

    print(f"[lector] Nodos libro en grafo:     {G.number_of_nodes() - len(NODOS_FIJOS) - len(nodos_genero_añadidos)}")
    print(f"[lector] Referencias entre libros: {len(referencias)}")

    return G, referencias


def leer_likes(ruta_json):
  
    with open(ruta_json, 'r', encoding='utf-8') as f:
        libros = json.load(f)

    ratings_data = {}
    for libro in libros:
        bid = libro.get("book_id")
        if not bid:
            continue
        try:
            avg = float(libro.get("average_rating") or 0)
        except (ValueError, TypeError):
            avg = 0.0
        try:
            count = int(libro.get("ratings_count") or 0)
        except (ValueError, TypeError):
            count = 0
        ratings_data[bid] = {
            "average_rating": avg,
            "ratings_count":  count,
        }
    return ratings_data