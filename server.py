import socket
import json
import demov5  # Importamos tu lógica directamente

def iniciar_servidor():
    HOST, PORT = '127.0.0.1', 8080
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(1)
    print(f"🚀 Servidor de Grafos listo en http://{HOST}:{PORT}")

    while True:
        conn, addr = server.accept()
        peticion = conn.recv(2048).decode('utf-8')
        
        if peticion:
            # --- SOPORTE PARA CORS (Preflight) ---
            # El navegador preguntará primero con OPTIONS si puede hablar contigo
            if peticion.startswith('OPTIONS'):
                respuesta = "HTTP/1.1 204 No Content\r\n" \
                            "Access-Control-Allow-Origin: *\r\n" \
                            "Access-Control-Allow-Methods: POST, OPTIONS\r\n" \
                            "Access-Control-Allow-Headers: Content-Type\r\n" \
                            "\r\n"
                conn.sendall(respuesta.encode())
                conn.close()
                continue

            try:
                # --- EJECUCIÓN DE TU LÓGICA ---
                # Usamos las funciones que ya tienes en demov5.py
                G = demov5.leer_entrada("entrada.txt")
                referencias = [("Historical mystery", "Detective mystery"), ("Mystery thriller", "Psychological thriller")]
                likes = demov5.likes_libros
                
                v1 = demov5.version1_sin_pesos(G)
                v3 = demov5.version3_con_referencias_y_pesos(G, referencias)
                v4 = demov5.version4_personalizacion_likes(G, likes, referencias)

                # Preparamos los datos para enviarlos a la web
                nodos_data = []
                for nodo in sorted(v1.keys()):
                    nodos_data.append({
                        "nombre": nodo,
                        "v1": round(v1[nodo], 6),
                        "v3": round(v3[nodo], 6),
                        "v4": round(v4[nodo], 6)
                    })

                cuerpo_json = json.dumps(nodos_data)
                
                # --- RESPUESTA HTTP ---
                respuesta_http = (
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: application/json\r\n"
                    "Access-Control-Allow-Origin: *\r\n"
                    f"Content-Length: {len(cuerpo_json)}\r\n"
                    "\r\n"
                    f"{cuerpo_json}"
                )
                conn.sendall(respuesta_http.encode('utf-8'))
                
            except Exception as e:
                print(f"❌ Error procesando: {e}")
                
        conn.close()

if __name__ == "__main__":
    iniciar_servidor()