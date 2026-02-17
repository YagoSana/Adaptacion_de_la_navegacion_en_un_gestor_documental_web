import logging

def imprimir_grafo(G, titulo):
    print(f"\n========== {titulo} ==========")
    
    # Empezar por los nodos que tienen nivel 0 (raíz)
    raices_reales = [n for n, attr in G.nodes(data=True) if attr.get('nivel') == 0]
    
    # Usar un for por si hubiera múltiples raíces pero deberia haber una solo
    for raiz in sorted(raices_reales):
        print(f"[{raiz}]")
        _imprimir_recursivo_tree(G, raiz, "")

def _imprimir_recursivo_tree(G, nodo_actual, prefijo):
    # Obtenemos el nivel del nodo actual para solo ir a niveles superiores
    nivel_actual = G.nodes[nodo_actual].get('nivel', 0)
    
    # Filtramos vecinos que tengan un nivel mayor al actual (para asegurar que bajamos en el árbol)
    hijos = []
    for vecino in G.neighbors(nodo_actual):
        nivel_vecino = G.nodes[vecino].get('nivel', 0)
        if nivel_vecino > nivel_actual:
            hijos.append(vecino)
    
    hijos.sort() # Orden alfabético para los hermanos
    num_hijos = len(hijos)
    
    for i, hijo in enumerate(hijos):
        es_ultimo = (i == num_hijos - 1)
        conector = "└── " if es_ultimo else "├── "
        
        print(f"{prefijo}{conector}{hijo}")
        
        nuevo_prefijo = prefijo + ("    " if es_ultimo else "│   ")
        _imprimir_recursivo_tree(G, hijo, nuevo_prefijo)

def imprimir_arbol_con_pesos(G, pr, titulo):
    """
    Imprime el árbol con los valores de PageRank al lado de cada nodo
    """
    print(f"\n{'='*70}")
    print(f"{titulo}")
    print(f"{'='*70}\n")
    
    # Empezar por los nodos que tienen nivel 0 (raíz)
    raices_reales = [n for n, attr in G.nodes(data=True) if attr.get('nivel') == 0]
    
    Azul = "\033[34m"
    Reset = "\033[0m"

    for raiz in sorted(raices_reales):
        score = pr.get(raiz, 0)
        print(f"[{raiz}] {Azul}{score:.6f}{Reset}")
        _imprimir_recursivo_con_pesos(G, raiz, "", pr)


def _imprimir_recursivo_con_pesos(G, nodo_actual, prefijo, pr):
    """
    Función recursiva para imprimir árbol con pesos
    """
    nivel_actual = G.nodes[nodo_actual].get('nivel', 0)
    
    # Filtramos vecinos que tengan un nivel mayor al actual
    hijos = []
    for vecino in G.neighbors(nodo_actual):
        nivel_vecino = G.nodes[vecino].get('nivel', 0)
        if nivel_vecino > nivel_actual:
            hijos.append(vecino)
    
    hijos.sort()
    num_hijos = len(hijos)

    Azul = "\033[34m"
    Reset = "\033[0m"
    
    for i, hijo in enumerate(hijos):
        es_ultimo = (i == num_hijos - 1)
        conector = "└── " if es_ultimo else "├── "
        score = pr.get(hijo, 0)
        
        print(f"{prefijo}{conector}{hijo} {Azul}{score:.6f}{Reset}")
        
        nuevo_prefijo = prefijo + ("    " if es_ultimo else "│   ")
        _imprimir_recursivo_con_pesos(G, hijo, nuevo_prefijo, pr)


def tabla_comparativa_final(G, pr_v1, pr_v2, pr_v3):
    """
    Tabla comparativa única y completa de las tres versiones con análisis
    """
    print(f"\n{'='*90}")
    print("TABLA COMPARATIVA FINAL - TODAS LAS VERSIONES")
    print(f"{'='*90}")
    
    # Ordenar por V1 para mantener consistencia
    nodos_ordenados = sorted(pr_v1.items(), key=lambda x: x[1], reverse=True)
    
    print(f"\n{'Nodo':<35} {'V1 (base)':<15} {'V2 (pesos)':<15} {'V3 (refs)':<15} {'ΔV2':<10} {'ΔV3':<10}")
    print("-"*90)
    
    for nodo, score_v1 in nodos_ordenados:
        score_v2 = pr_v2[nodo]
        score_v3 = pr_v3[nodo]
        diff_v2 = score_v2 - score_v1
        diff_v3 = score_v3 - score_v1
        
        print(f"{nodo:<35} {score_v1:<15.6f} {score_v2:<15.6f} {score_v3:<15.6f} {diff_v2:+<10.4f} {diff_v3:+<10.4f}")
    