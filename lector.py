import networkx as nx

def leer_entrada(nombre_archivo):
    G = nx.DiGraph()
    last_nodes = {}

    with open(nombre_archivo, 'r') as f:
        for line in f:
            # Ignoramos líneas vacías
            stripped = line.strip()
            if not stripped: continue
            
            # Limpiamos el nombre del nodo si tiene asteriscos
            node_name = stripped.replace("**", "").strip()

            # Calculamos el nivel segun la cantidad de tabs (0 para la raíz, >0 para hijos)
            indent = len(line) - len(line.lstrip())
            
            # Guardamos el nodo con su atributo de nivel
            G.add_node(node_name, nivel=indent)
            last_nodes[indent] = node_name
            
            if indent > 0:
                # Buscamos el padre en el nivel superior más cercano
                parent_levels = [lvl for lvl in last_nodes.keys() if lvl < indent]
                if parent_levels:
                    parent_name = last_nodes[max(parent_levels)]
                    # Creamos la relación bidireccional
                    G.add_edge(parent_name, node_name)
                    G.add_edge(node_name, parent_name)
    return G