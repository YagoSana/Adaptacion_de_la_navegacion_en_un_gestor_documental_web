import networkx as nx
from lector import leer_entrada, leer_likes
from imprimir import imprimir_arbol_con_pesos

def version_personalizacion_likes(G, likes_libros, referencias=None, peso_libros=3, peso_ref=3, alpha=0.85):
    """
    PageRank personalizado donde:
    - Cada libro tiene un número de likes 
    - El vector de personalización concentra importancia en los libros
    - Las referencias (similar_books) añaden aristas cruzadas entre géneros
    """
    if referencias is None:
        referencias = []

    # Identificar nodos hoja (libros): máximo nivel en el grafo
    niveles = [G.nodes[n].get('nivel', 0) for n in G.nodes()]
    max_nivel = max(niveles) if niveles else 0

    nodos_hoja = {n for n in G.nodes() if G.nodes[n].get('nivel', 0) == max_nivel}

    # Crear grafo bidireccional con pesos
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

    # Vector de personalización basado en likes (ratings_count)
    total_likes = sum(likes_libros.values()) or 1

    personalization = {}
    for nodo in G_completo.nodes():
        if nodo in likes_libros:
            personalization[nodo] = (likes_libros[nodo] * peso_libros * 10) / total_likes
        else:
            personalization[nodo] = 0.0

    # Normalizar (PageRank requiere que sumen > 0)
    total_p = sum(personalization.values())
    if total_p > 0:
        personalization = {k: v / total_p for k, v in personalization.items()}

    pr = nx.pagerank(G_completo, alpha=alpha, personalization=personalization, weight='weight')

    return pr


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

DATASET = "dataset_limpio.json"

G, referencias = leer_entrada(DATASET)
likes_libros   = leer_likes(DATASET)

peso_libros = 3
peso_ref    = 3

pr = version_personalizacion_likes(G, likes_libros, referencias, peso_libros, peso_ref)

imprimir_arbol_con_pesos(G, pr, "Personalización por Likes (dataset Goodreads)")