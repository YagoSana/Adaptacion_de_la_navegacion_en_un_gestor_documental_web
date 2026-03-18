import networkx as nx
from lector import leer_entrada, leer_likes

# ---------------------------------------------------------------------------
# Promedio ponderado bayesiano
#
#   Score = (v / (v + m)) * R  +  (m / (v + m)) * C
#
#   R = average_rating del libro  (puede ser el del usuario si lo valoró)
#   v = ratings_count del libro
#   C = promedio global de todos los average_rating
#   m = umbral mínimo de votos (percentil 50 por defecto)
# ---------------------------------------------------------------------------

def _bayesian_scores(ratings_data: dict, percentil_m: float = 0.5) -> dict:

    if not ratings_data:
        return {}

    counts  = [d["ratings_count"]  for d in ratings_data.values()]
    ratings = [d["average_rating"] for d in ratings_data.values()]

    C = sum(ratings) / len(ratings)

    counts_sorted = sorted(counts)
    idx = int(len(counts_sorted) * percentil_m)
    m   = counts_sorted[min(idx, len(counts_sorted) - 1)]

    scores = {}
    for nodo, d in ratings_data.items():
        v = d["ratings_count"]
        R = d["average_rating"]
        scores[nodo] = (v / (v + m)) * R + (m / (v + m)) * C

    return scores


def version_personalizacion_likes(
    G,
    ratings_data,
    referencias=None,
    peso_libros=3,
    peso_ref=3,
    alpha=0.85,
    percentil_m=0.5,
    user_ratings=None,        # { book_id: 1-5 }
    user_genre_ratings=None,  # { node_id: 1-5 } — géneros y subcategorías
    debug_mode=False,
):
    """
    PageRank personalizado.

    Modo normal:  el vector de personalización usa el score bayesiano de todos
                  los libros, sustituyendo average_rating por la valoración del
                  usuario cuando existe.

    Modo debug:   el vector de personalización arranca a 0 para todos los nodos.
                  Solo los libros que el usuario ha valorado explícitamente
                  reciben peso (proporcional a su número de estrellas).
                  Así el PageRank refleja única y directamente las preferencias
                  del usuario, sin influencia del dataset.
    """
    if referencias is None:
        referencias = []
    if user_ratings is None:
        user_ratings = {}
    if user_genre_ratings is None:
        user_genre_ratings = {}

    # Identificar nodos hoja (libros)
    niveles    = [G.nodes[n].get('nivel', 0) for n in G.nodes()]
    max_nivel  = max(niveles) if niveles else 0
    nodos_hoja = {n for n in G.nodes() if G.nodes[n].get('nivel', 0) == max_nivel}

    # Grafo bidireccional con pesos (igual en ambos modos)
    G_completo = nx.DiGraph()
    G_completo.add_nodes_from(G.nodes(data=True))

    referencias_set = set(map(tuple, referencias))

    for u, v in G.edges():
        if (u, v) not in referencias_set:
            peso = peso_libros if v in nodos_hoja else 1.0
            G_completo.add_edge(u, v, weight=peso)
            G_completo.add_edge(v, u, weight=peso)

    for u, v in referencias:
        if G_completo.has_node(u) and G_completo.has_node(v):
            G_completo.add_edge(u, v, weight=peso_ref)
            G_completo.add_edge(v, u, weight=peso_ref)

    # ── Vector de personalización ─────────────────────────────────────────────
    if debug_mode:
        # Todos los nodos arrancan a 0
        personalization = {nodo: 0.0 for nodo in G_completo.nodes()}

        # Peso de libros valorados por el usuario
        for book_id, estrellas in user_ratings.items():
            if estrellas > 0 and book_id in personalization:
                personalization[book_id] = float(estrellas)

        # Peso de géneros/categorías valorados por el usuario
        for node_id, estrellas in user_genre_ratings.items():
            if estrellas > 0 and node_id in personalization:
                personalization[node_id] = float(estrellas)

        total_p = sum(personalization.values())
        if total_p > 0:
            personalization = {k: v / total_p for k, v in personalization.items()}
        else:
            # Sin ninguna valoración: PageRank uniforme
            personalization = None

    else:
        # Modo normal: score bayesiano con valoraciones del usuario aplicadas
        ratings_data_efectivo = {}
        for book_id, d in ratings_data.items():
            if book_id in user_ratings and user_ratings[book_id] > 0:
                ratings_data_efectivo[book_id] = {
                    "average_rating": float(user_ratings[book_id]),
                    "ratings_count":  d["ratings_count"],
                }
            else:
                ratings_data_efectivo[book_id] = d

        bayesian = _bayesian_scores(ratings_data_efectivo, percentil_m)

        personalization = {}
        for nodo in G_completo.nodes():
            if nodo in bayesian:
                personalization[nodo] = bayesian[nodo] * peso_libros * 10
            else:
                personalization[nodo] = 0.0

        total_p = sum(personalization.values())
        if total_p > 0:
            personalization = {k: v / total_p for k, v in personalization.items()}

    pr = nx.pagerank(G_completo, alpha=alpha, personalization=personalization, weight='weight')

    return pr