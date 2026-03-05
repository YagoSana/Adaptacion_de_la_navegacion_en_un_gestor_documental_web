import socket
import json
import lector
import logica

DATASET = "dataset_limpio.json"

def obtener_estructura_arbol(G, nodo_actual, valores):
    atributos = G.nodes[nodo_actual]

    nivel_actual = atributos.get('nivel', 0)
    hijos = [v for v in G.neighbors(nodo_actual) if G.nodes[v].get('nivel', 0) > nivel_actual]

    # Usar nombre legible si existe, si no usar ID
    nombre = atributos.get('display', nodo_actual)

    # Construimos el diccionario base (carpetas y libros lo tienen)
    nodo_dict = {
        "nombre": nombre,
        "id":     nodo_actual,
        "valor":  round(valores.get(nodo_actual, 0), 6),
        "hijos":  [obtener_estructura_arbol(G, h, valores) for h in sorted(hijos)]
    }
    
    # Si es un nodo hoja le inyectamos toda la información extra que viene de lector.py
    if len(hijos) == 0:
        nodo_dict["title"]            = atributos.get("title")
        nodo_dict["authors"]          = atributos.get("authors")
        nodo_dict["genero"]           = atributos.get("genero")
        nodo_dict["descripcion"]      = atributos.get("descripcion")
        nodo_dict["average_rating"]   = atributos.get("average_rating")
        nodo_dict["ratings_count"]    = atributos.get("ratings_count")
        nodo_dict["publisher"]        = atributos.get("publisher")
        nodo_dict["num_pages"]        = atributos.get("num_pages")
        nodo_dict["publication_year"] = atributos.get("publication_year")
        nodo_dict["isbn"]             = atributos.get("isbn")
        nodo_dict["similar_books"]    = atributos.get("similar_books", [])
        nodo_dict["tiene_similar"]    = atributos.get("tiene_similar", False)

    return nodo_dict


def iniciar_servidor():
    HOST, PORT = '127.0.0.1', 8080
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(1)
    print(f"🚀 Servidor listo en http://{HOST}:{PORT}")

    # Precargamos el grafo y los likes una sola vez
    print(f"Cargando dataset {DATASET}...")
    G, referencias = lector.leer_entrada(DATASET)
    ratings_data = lector.leer_likes(DATASET)
    print("Dataset cargado.")

    while True:
        conn, addr = server.accept()
        peticion = conn.recv(2048).decode('utf-8')

        if peticion:
            if peticion.startswith('OPTIONS'):
                respuesta = ("HTTP/1.1 204 No Content\r\n"
                             "Access-Control-Allow-Origin: *\r\n"
                             "Access-Control-Allow-Methods: POST, OPTIONS\r\n"
                             "Access-Control-Allow-Headers: Content-Type\r\n"
                             "\r\n")
                conn.sendall(respuesta.encode())
                conn.close()
                continue

            try:
                partes = peticion.split('\r\n\r\n')
                if len(partes) > 1:
                    body_data = json.loads(partes[1])
                    p_libro = body_data.get('peso_libro', 3.0)
                    p_ref   = body_data.get('peso_referencia', 3.0)
                else:
                    p_libro, p_ref = 3.0, 3.0

                print(f"Calculando PageRank (peso_libro={p_libro}, peso_ref={p_ref})...")
                valores = logica.version_personalizacion_likes(G, ratings_data, referencias, p_libro, p_ref)

                # Tabla global ordenada por valor
                nodos_data = [
                    {"nombre": G.nodes[n].get('display', n), "id": n, "valor": round(v, 6)}
                    for n, v in valores.items()
                ]

                # Árbol jerárquico
                raices = [n for n, attr in G.nodes(data=True) if attr.get('nivel') == 0]
                raiz = raices[0] if raices else None
                arbol = obtener_estructura_arbol(G, raiz, valores) if raiz else {}

                respuesta_final = {"tabla": nodos_data, "arbol": arbol}
                cuerpo_json = json.dumps(respuesta_final)

                respuesta_http = (
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: application/json\r\n"
                    "Access-Control-Allow-Origin: *\r\n"
                    f"Content-Length: {len(cuerpo_json.encode('utf-8'))}\r\n"
                    "\r\n"
                    f"{cuerpo_json}"
                )
                conn.sendall(respuesta_http.encode('utf-8'))

            except Exception as e:
                print(f"Error: {e}")

        conn.close()


if __name__ == "__main__":
    iniciar_servidor()