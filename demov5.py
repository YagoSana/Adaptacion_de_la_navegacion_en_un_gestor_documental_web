import networkx as nx
from lector import leer_entrada
from imprimir import imprimir_arbol_con_pesos, tabla_comparativa_final
#from generaHTML import exportar_html
import logging


def version1_sin_pesos(G, alpha=0.85):
    """
    PageRank básico sobre jerarquías bidireccionales.
    Todas las relaciones valen igual.
    """
    # Crear grafo bidireccional
    G_bi = nx.DiGraph()
    G_bi.add_nodes_from(G.nodes(data=True))
    
    # Hacer bidireccionales las relaciones jerárquicas
    for u, v in G.edges():
        G_bi.add_edge(u, v)
        G_bi.add_edge(v, u)
    
    # PageRank sin pesos
    pr = nx.pagerank(G_bi, alpha=alpha)
    
    return pr


def version4_personalizacion_likes(G, likes_libros, referencias=None, alpha=0.85):
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
            personalization[nodo] = likes_libros[nodo] / total_likes
        else:
            # Nodos intermedios (categorías) empiezan con 0
            personalization[nodo] = 0.0
    
    # PageRank con personalización
    pr = nx.pagerank(G_completo, alpha=alpha, personalization=personalization)
    
    return pr


def version3_con_referencias_y_pesos(G, referencias, peso_libro=2.0, peso_referencia=3.0, alpha=0.85):
    """
    PageRank con:
    - Pesos a libros (nodos hoja)
    - Referencias cruzadas con su propio peso
    """
    # Identificar nodos hoja usando nivel máximo
    niveles = [G.nodes[n].get('nivel', 0) for n in G.nodes()]
    max_nivel = max(niveles) if niveles else 0
    
    nodos_hoja = set()
    for nodo in G.nodes():
        if G.nodes[nodo].get('nivel', 0) == max_nivel:
            nodos_hoja.add(nodo)
    
    # Crear grafo completo
    G_completo = nx.DiGraph()
    G_completo.add_nodes_from(G.nodes(data=True))
    
    # Añadir relaciones jerárquicas con pesos
    referencias_set = set(referencias)
    for u, v in G.edges():
        # Solo si no es una referencia
        if (u, v) not in referencias_set:
            peso = peso_libro if v in nodos_hoja else 1.0
            G_completo.add_edge(u, v, weight=peso)
            G_completo.add_edge(v, u, weight=peso)
    
    # Añadir referencias con su peso
    for u, v in referencias:
        G_completo.add_edge(u, v, weight=peso_referencia)
        G_completo.add_edge(v, u, weight=peso_referencia)
    
    # PageRank con pesos
    pr = nx.pagerank(G_completo, alpha=alpha, weight='weight')
    
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

print("EJECUTANDO LAS 3 VERSIONES DEL ALGORITMO")

pr_v1 = version1_sin_pesos(G)
pr_v3 = version3_con_referencias_y_pesos(G, referencias, peso_libro=2.0, peso_referencia=3.0)
pr_v4 = version4_personalizacion_likes(G, likes_libros, referencias)

# MOSTRAR ÁRBOLES CON PESOS
imprimir_arbol_con_pesos(G, pr_v1, "VERSIÓN 1: Sin Pesos (Baseline)")
imprimir_arbol_con_pesos(G, pr_v3, "VERSIÓN 3: Con Referencias y Pesos (refs=3x, libros=2x)")
imprimir_arbol_con_pesos(G, pr_v4, "VERSIÓN 4: Personalización por Likes")

tabla_comparativa_final(G, pr_v1, pr_v3, pr_v4)

#exportar_html(G, pr_v1, pr_v3, pr_v4, "index.html")