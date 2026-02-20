import networkx as nx
from lector import leer_entrada
from imprimir import imprimir_arbol_con_pesos

def version_personalizacion_likes(G, likes_libros, referencias=None, peso_libros=3, peso_ref=3, alpha=0.85):
    """
    PageRank personalizado donde:
    - Cada libro tiene un número de likes (rating)
    - El vector de personalización concentra importancia en los libros
    - Las categorías superiores heredan importancia de sus libros
    
    """
    # Identificar nodos hoja (libros)
    niveles = [G.nodes[n].get('nivel', 0) for n in G.nodes()]
    max_nivel = max(niveles) if niveles else 0
    
    nodos_hoja = set()
    for nodo in G.nodes():
        if G.nodes[nodo].get('nivel', 0) == max_nivel:
            nodos_hoja.add(nodo)
    
    # Crear grafo bidireccional
    G_completo = nx.DiGraph()
    G_completo.add_nodes_from(G.nodes(data=True))
    
    # Añadir jerarquías bidireccionales
    referencias_set = set(referencias) if referencias else set()
    for u, v in G.edges():
        if (u, v) not in referencias_set:
            G_completo.add_edge(u, v)
            G_completo.add_edge(v, u)
    
    # Añadir referencias si existen
    if referencias:
        for u, v in referencias:
            G_completo.add_edge(u, v)
            G_completo.add_edge(v, u)
    
    # CREAR VECTOR DE PERSONALIZACIÓN basado en likes
    # Solo los libros (hojas) reciben importancia inicial
    total_likes = sum(likes_libros.values())
    
    personalization = {}
    for nodo in G_completo.nodes():
        if nodo in likes_libros:
            # Normalizar: cada libro tiene peso proporcional a sus likes
            personalization[nodo] = ((likes_libros[nodo] * peso_libros) / total_likes)
        else:
            # Nodos intermedios (categorías) empiezan con 0
            personalization[nodo] = 0.0
    
    # PageRank con personalización
    pr = nx.pagerank(G_completo, alpha=alpha, personalization=personalization)
    
    return pr


# ============================================================================
# PROGRAMA PRINCIPAL
# ============================================================================

G = leer_entrada("entrada.txt")

referencias = [
    ("Historical mystery", "Detective mystery"),
    ("Mystery thriller", "Psychological thriller"),
]

# DEFINIR LIKES POR LIBRO (simulando popularidad)
likes_libros = {
    # Historical fiction
    "Christian Historical Fiction": 100,
    "Historical mystery": 500,              # POPULAR
    "Biographical": 150,
    "Alternate history": 200,
    "Historical adventure": 180,
    
    # Crime
    "Detective crime": 300,
    "Noir crime": 250,
    "Hard boiled crime": 220,
    
    # Mystery
    "Detective mystery": 450,               # POPULAR
    "Cozy mystery": 400,
    "Murder mystery": 380,
    "Paranormal mystery": 150,
    # "Historical mystery" ya tiene la popularidad
    
    # Thriller
    "Mystery thriller": 600,                # MUY POPULAR
    "Psychological thriller": 700,          # MUY POPULAR
    "Spy thriller": 350,
    "Legal thriller": 280,
    "Medical thriller": 260,
    "Supernatural thriller": 200,
    
    # Suspense
    "Love-inspired suspense": 180,
}

peso_libros = 3
peso_ref = 3

pr_v4 = version_personalizacion_likes(G, likes_libros, referencias, peso_libros, peso_ref)

# MOSTRAR 
imprimir_arbol_con_pesos(G, pr_v4, "Personalización por Likes")