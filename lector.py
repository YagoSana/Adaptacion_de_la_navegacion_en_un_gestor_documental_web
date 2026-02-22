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
    "Crime": {
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
    "Mystery": {
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
    "Thriller": {
        "padre": "Fiction",
        "subgrupo": "Mystery&Crime fiction/Thriller"
    },
    "Love-inspired suspense": {
        "padre": "Fiction",
        "subgrupo": "Mystery&Crime fiction/Suspense"
    },
    "Suspense": {
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

    # Índice book_id -> libro (para resolver similar_books después)
    indice = {l["book_id"]: l for l in libros if l.get("book_id")}

    nodos_genero_añadidos = set()
    referencias = []

    for libro in libros:
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

        # Añadir nodo libro (nivel hoja)
        nivel_libro = nivel_genero + 1
        G.add_node(book_id, nivel=nivel_libro, display=title,
                   title=title,
                   average_rating=float(libro.get("average_rating") or 0),
                   ratings_count=int(libro.get("ratings_count") or 0))
        G.add_edge(genero, book_id)

        # Recopilar referencias (similar_books dentro del dataset)
        for similar_id in libro.get("similar_books", []):
            if similar_id in indice and similar_id != book_id:
                referencias.append((book_id, similar_id))

    print(f"[lector] Libros cargados: {G.number_of_nodes() - len(NODOS_FIJOS) - len(nodos_genero_añadidos)}")
    print(f"[lector] Referencias entre libros: {len(referencias)}")

    return G, referencias


def leer_likes(ruta_json):
    """
    Devuelve un dict {book_id: average_rating} para usar como peso en logica.py
    """
    with open(ruta_json, 'r', encoding='utf-8') as f:
        libros = json.load(f)

    likes = {}
    for libro in libros:
        bid = libro.get("book_id")
        rating = libro.get("average_rating", 0)
        if bid:
            try:
                likes[bid] = float(rating)
            except (ValueError, TypeError):
                likes[bid] = 0.0
    return likes