import socket
import json
import lector  
import logica

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
                # Usamos las funciones que ya hay en logica.py
                G = lector.leer_entrada("entrada.txt")
                referencias = [("Historical mystery", "Detective mystery"), ("Mystery thriller", "Psychological thriller")]
                
                # Likes asociados al dataset, actualmente a mano
                likes = logica.likes_libros
                
                valores = logica.version_personalizacion_likes(G, likes, referencias)

                # Preparamos los datos para enviarlos a la web
                nodos_data = []
                for nodo in sorted(valores.keys()):
                    nodos_data.append({
                        "nombre": nodo,
                        "valor": round(valores[nodo], 6)
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
                print(f"Error durante el proceso: {e}")
                
        conn.close()

if __name__ == "__main__":
    iniciar_servidor()