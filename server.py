import socket
import json
import lector
import logica

DATASET = "dataset_limpio.json"

# Renombrado de nodos para datasets de prueba (display only, los IDs no cambian)
DATASET_DISPLAYS = {
    "dataset_B1.json": {
        "Mystery&Crime fiction/Crime":    "Crimen",
        "Mystery&Crime fiction/Suspense": "Terror gótico",
    },
    "dataset_B2.json": {
        "Mystery&Crime fiction/Crime":    "Crimen",
        "Mystery&Crime fiction/Suspense": "Terror gótico",
    },
}

def obtener_estructura_arbol(G, nodo_actual, valores, sort_values=None, scores_efectivos=None):
    if sort_values is None:
        sort_values = valores
    if scores_efectivos is None:
        scores_efectivos = {}
    atributos    = G.nodes[nodo_actual]
    nivel_actual = atributos.get('nivel', 0)
    hijos        = [v for v in G.neighbors(nodo_actual)
                    if G.nodes[v].get('nivel', 0) > nivel_actual]

    # Ordenar por sort_values descendente (más alto primero), id como desempate
    hijos.sort(key=lambda h: (-sort_values.get(h, 0), h))

    nombre = atributos.get('display', nodo_actual)

    nodo_dict = {
        "nombre": nombre,
        "id":     nodo_actual,
        "valor":  round(valores.get(nodo_actual, 0), 6),
        "hijos":  [obtener_estructura_arbol(G, h, valores, sort_values, scores_efectivos) for h in hijos]
    }

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
        # Score que la app está usando ahora mismo (bayesiano o raw según el prior)
        if nodo_actual in scores_efectivos:
            nodo_dict["score_efectivo"] = round(scores_efectivos[nodo_actual], 6)

    return nodo_dict


def iniciar_servidor():
    HOST, PORT = '127.0.0.1', 8080
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(1)
    print(f"Servidor listo en http://{HOST}:{PORT}  (Ctrl+C para parar)")

    print(f"Cargando dataset {DATASET}...")
    import re
    es_prueba = bool(re.match(r"^dataset_[A-Z]\d", DATASET))
    overrides = DATASET_DISPLAYS.get(DATASET)
    G, referencias = lector.leer_entrada(DATASET, simplificar=es_prueba, display_overrides=overrides)
    ratings_data   = lector.leer_likes(DATASET)
    print(f"Dataset cargado. (simplificar={es_prueba}, overrides={bool(overrides)})")

    while True:
        conn, addr = server.accept()

        # Leer petición completa (puede ser grande si hay muchos ratings)
        datos = b''
        while True:
            chunk = conn.recv(4096)
            datos += chunk
            if len(chunk) < 4096:
                break
        peticion = datos.decode('utf-8')

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

            # Ignorar todo lo que no sea POST (GET del navegador, favicon, etc.)
            if not peticion.startswith('POST'):
                respuesta = "HTTP/1.1 405 Method Not Allowed\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: 0\r\n\r\n"
                conn.sendall(respuesta.encode())
                conn.close()
                continue

            try:
                partes = peticion.split('\r\n\r\n', 1)
                if len(partes) > 1 and partes[1].strip():
                    body_data          = json.loads(partes[1])
                    p_libro            = body_data.get('peso_libro', 3.0)
                    p_ref              = body_data.get('peso_referencia', 3.0)
                    user_ratings       = body_data.get('user_ratings', {})
                    user_genre_ratings = body_data.get('user_genre_ratings', {})
                    debug_mode         = body_data.get('debug_mode', False)
                    baseline           = body_data.get('baseline', False)
                    aplicar_prior      = body_data.get('aplicar_prior', True)
                else:
                    p_libro, p_ref = 3.0, 3.0
                    user_ratings   = {}
                    user_genre_ratings = {}
                    debug_mode = False
                    baseline   = False
                    aplicar_prior = True

                # Calcular scores efectivos: lo que se usa como R para cada libro
                # (bayesiano cuando aplicar_prior=True, raw average_rating cuando False)
                ratings_eff = logica.ratings_efectivos(G, ratings_data, user_ratings, user_genre_ratings)
                scores_efectivos = logica._bayesian_scores(ratings_eff, aplicar_prior=aplicar_prior)

                if baseline:
                    print(f"Modo baseline: orden por bayesiano efectivo (prior={aplicar_prior}).")
                    # sort_values = bayesiano → ordena el árbol
                    sort_values = {n: 0.0 for n in G.nodes()}
                    for book_id, score in scores_efectivos.items():
                        if book_id in sort_values:
                            sort_values[book_id] = score
                    # valores = 0 -> la badge "PR" mostrará 0 porque aún no se ha calculado
                    valores = {n: 0.0 for n in G.nodes()}
                else:
                    print(f"Calculando PageRank (peso_libro={p_libro}, peso_ref={p_ref}, "
                          f"libros valorados={len(user_ratings)}, géneros valorados={len(user_genre_ratings)}, "
                          f"debug_mode={debug_mode}, aplicar_prior={aplicar_prior})...")

                    valores = logica.version_personalizacion_likes(
                        G, ratings_data, referencias,
                        p_libro, p_ref,
                        user_ratings=user_ratings,
                        user_genre_ratings=user_genre_ratings,
                        debug_mode=debug_mode,
                        aplicar_prior=aplicar_prior,
                    )
                    sort_values = valores

                nodos_data = [
                    {"nombre": G.nodes[n].get('display', n), "id": n, "valor": round(v, 6)}
                    for n, v in valores.items()
                ]

                raices = [n for n, attr in G.nodes(data=True) if attr.get('nivel') == 0]
                raiz   = raices[0] if raices else None
                arbol  = obtener_estructura_arbol(G, raiz, valores, sort_values, scores_efectivos) if raiz else {}

                respuesta_final = {
                    "tabla": nodos_data,
                    "arbol": arbol,
                    "modo": "baseline" if baseline else "pagerank",
                    "aplicar_prior": aplicar_prior,
                }
                cuerpo_json     = json.dumps(respuesta_final)

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
                import traceback
                print(f"Error: {e}")
                traceback.print_exc()

        conn.close()


if __name__ == "__main__":
    try:
        iniciar_servidor()
    except KeyboardInterrupt:
        print("\n Servidor detenido por el usuario (Ctrl+C).")