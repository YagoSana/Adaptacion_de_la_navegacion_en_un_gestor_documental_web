import networkx as nx
from lector import leer_entrada, leer_likes

# ---------------------------------------------------------------------------
# Promedio ponderado bayesiano 
#
#   Score = (v / (v + m)) * R  +  (m / (v + m)) * C
#
#   R = average_rating del libro
#   v = ratings_count del libro
#   C = promedio global de todos los average_rating
#   m = umbral mínimo de votos (percentil 50 por defecto)
# ---------------------------------------------------------------------------

def _bayesian_scores(ratings_data: dict, percentil_m: float = 0.5) -> dict:
    
    if not ratings_data:
        return {}

    counts  = [d["ratings_count"]  for d in ratings_data.values()]
    ratings = [d["average_rating"] for d in ratings_data.values()]

    # C: promedio global de valoraciones
    C = sum(ratings) / len(ratings)

    # m: umbral mínimo de votos (percentil indicado)
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
):
    """
    PageRank personalizado donde:
    - El vector de personalización se basa en el score bayesiano de cada libro
      (combina average_rating y ratings_count de forma justa).
    - Las referencias (similar_books) añaden aristas cruzadas entre géneros.
    """
    if referencias is None:
        referencias = []

    # --- Score bayesiano por libro ----------------------------------------
    bayesian = _bayesian_scores(ratings_data, percentil_m)

    # --- Identificar nodos hoja (libros): máximo nivel en el grafo ---------
    niveles   = [G.nodes[n].get('nivel', 0) for n in G.nodes()]
    max_nivel = max(niveles) if niveles else 0
    nodos_hoja = {n for n in G.nodes() if G.nodes[n].get('nivel', 0) == max_nivel}

    # --- Grafo bidireccional con pesos -------------------------------------
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

    # --- Vector de personalización (scores bayesianos normalizados) --------
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


# ============================================================
# PROGRAMA PRINCIPAL (ejecución directa, no necesaria desde server.py)
# ============================================================

# DATASET = "dataset_limpio.json"
#
# G, referencias  = leer_entrada(DATASET)
# ratings_data    = leer_likes(DATASET)   # ahora devuelve {nodo: {"average_rating": float, "ratings_count": int}}
#
# peso_libros = 3
# peso_ref    = 3
#
# pr = version_personalizacion_likes(G, ratings_data, referencias, peso_libros, peso_ref)
#
# La impresión por consola ya no es necesaria: la visualización se realiza desde la interfaz web.