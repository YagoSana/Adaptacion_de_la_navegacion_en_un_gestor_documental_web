import networkx as nx
from collections import deque

# Código deprecated (versión anterior)
def _ancestro_rateado_cercano(G, nodo, user_genre_ratings):
    """
    BFS hacia arriba: devuelve la valoración del ancestro más cercano
    presente en user_genre_ratings (con valor > 0). None si ninguno.
    """
    visitados = {nodo}
    cola = deque([nodo])
    while cola:
        actual = cola.popleft()
        for padre in G.predecessors(actual):
            if padre in visitados:
                continue
            visitados.add(padre)
            if padre in user_genre_ratings and user_genre_ratings[padre] > 0:
                return float(user_genre_ratings[padre])
            cola.append(padre)
    return None


def ratings_efectivos(G, ratings_data, user_ratings, user_genre_ratings=None):
    """
    Aplica únicamente user_ratings sobre ratings_data:
    cada libro mantiene su average_rating salvo que el usuario
    haya rateado ese libro concreto. user_genre_ratings NO se
    propaga al R de los libros — su efecto sobre PageRank se
    aplica directamente al nodo de categoría en personalization.
    """
    user_ratings = user_ratings or {}
    resultado = {}
    for book_id, d in ratings_data.items():
        if book_id in user_ratings and user_ratings[book_id] > 0:
            effective_R = float(user_ratings[book_id])
        else:
            effective_R = float(d["average_rating"])
        resultado[book_id] = {
            "average_rating": effective_R,
            "ratings_count":  d["ratings_count"],
        }
    return resultado

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

def _bayesian_scores(ratings_data: dict, percentil_m: float = 0.5, aplicar_prior: bool = True) -> dict:

    if not ratings_data:
        return {}

    if not aplicar_prior:
        # Sin prior: devolver el rating crudo. Demuestra el problema
        # de no corregir libros con muy pocos votos.
        return {nodo: float(d["average_rating"]) for nodo, d in ratings_data.items()}

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
        if v + m == 0:
            scores[nodo] = C
        else:
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
    user_genre_ratings=None,  # { node_id: 1-5 } - géneros y subcategorías
    debug_mode=False,
    aplicar_prior=True,       # False = sin corrección bayesiana (raw average_rating)
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

    # Identificar nodos hoja (libros): los que no tienen hijos en el grafo.
    # No usamos nivel porque con árboles de profundidad mixta (p.ej. unas subcategorías con género intermedio y otras sin él)
    # algunas hojas quedarían fuera al filtrar por max_nivel.
    nodos_hoja = {n for n in G.nodes() if G.out_degree(n) == 0}

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

    # Vector de personalización
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
        # Modo normal: score bayesiano con valoraciones del usuario aplicadas.
        # Las valoraciones de género/categoría NO modifican el R de los libros. Actúan como un peso extra sobre el propio nodo 
        # de categoría en el vector de personalización.
        # PageRank lo propaga a los descendientes.
        ratings_data_efectivo = ratings_efectivos(G, ratings_data, user_ratings)
        bayesian = _bayesian_scores(ratings_data_efectivo, percentil_m, aplicar_prior=aplicar_prior)

        personalization = {}
        for nodo in G_completo.nodes():
            if nodo in bayesian:
                personalization[nodo] = bayesian[nodo] * peso_libros * 10
            else:
                personalization[nodo] = 0.0

        for node_id, estrellas in user_genre_ratings.items():
            if estrellas > 0 and node_id in personalization:
                personalization[node_id] += float(estrellas) * peso_libros * 10

        total_p = sum(personalization.values())
        if total_p > 0:
            personalization = {k: v / total_p for k, v in personalization.items()}
        else:
            # Sin ninguna señal (catálogo sin votos ni valoraciones del usuario):
            # PageRank con distribución uniforme. Evita ZeroDivisionError
            personalization = None

    pr = nx.pagerank(G_completo, alpha=alpha, personalization=personalization, weight='weight')

    return pr