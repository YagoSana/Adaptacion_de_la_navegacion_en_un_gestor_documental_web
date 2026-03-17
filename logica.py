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
    user_ratings=None,   # { book_id: 1-5 } — valoraciones personales del usuario
):
    """
    PageRank personalizado.
    Si user_ratings contiene una valoración para un libro, su average_rating
    se sustituye por esa valoración (escala 1-5) antes de calcular el score
    bayesiano, de modo que el cálculo refleja las preferencias del usuario.
    """
    if referencias is None:
        referencias = []
    if user_ratings is None:
        user_ratings = {}

    # Aplicar valoraciones del usuario sobre ratings_data
    # Hacemos una copia para no mutar el original (que se reutiliza entre peticiones)
    ratings_data_efectivo = {}
    for book_id, d in ratings_data.items():
        if book_id in user_ratings and user_ratings[book_id] > 0:
            # Sustituir average_rating por la valoración del usuario (1-5)
            ratings_data_efectivo[book_id] = {
                "average_rating": float(user_ratings[book_id]),
                "ratings_count":  d["ratings_count"],
            }
        else:
            ratings_data_efectivo[book_id] = d

    # Score bayesiano por libro 
    bayesian = _bayesian_scores(ratings_data_efectivo, percentil_m)

    # Identificar nodos hoja (libros) 
    niveles    = [G.nodes[n].get('nivel', 0) for n in G.nodes()]
    max_nivel  = max(niveles) if niveles else 0
    nodos_hoja = {n for n in G.nodes() if G.nodes[n].get('nivel', 0) == max_nivel}

    # Grafo bidireccional con pesos
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

    # Vector de personalización 
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