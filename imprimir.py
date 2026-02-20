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
