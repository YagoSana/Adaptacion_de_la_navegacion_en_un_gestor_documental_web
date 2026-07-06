import json
import gzip
import re
from collections import defaultdict

# MAPEO: shelves del dataset -> categorías del árbol
MAPEO_GENEROS = {
    # Historical fiction
    "historical-fiction":       "Historical fiction",
    "historical-mystery":       "Historical mystery",
    "christian-historical":     "Christian Historical Fiction",
    "biographical":             "Biographical",
    "biography":                "Biographical",
    "alternate-history":        "Alternate history",
    "historical-adventure":     "Historical adventure",

    # Crime
    "detective":                "Detective crime",
    "noir":                     "Noir crime",
    "hard-boiled":              "Hard boiled crime",
    "hardboiled":               "Hard boiled crime",
    "crime":                    "Generic crime",

    # Mystery
    "cozy-mystery":             "Cozy mystery",
    "cozy":                     "Cozy mystery",
    "murder-mystery":           "Murder mystery",
    "paranormal-mystery":       "Paranormal mystery",
    "mystery":                  "Generic mystery",

    # Thriller
    "psychological-thriller":   "Psychological thriller",
    "spy":                      "Spy thriller",
    "legal-thriller":           "Legal thriller",
    "medical-thriller":         "Medical thriller",
    "supernatural-thriller":    "Supernatural thriller",
    "mystery-thriller":         "Mystery thriller",
    "thriller":                 "Generic thriller",

    # Suspense
    "romantic-suspense":        "Love-inspired suspense",
    "love-inspired":            "Love-inspired suspense",
    "suspense":                 "Generic suspense",
}

# Mínimo de votos en un shelf para tomarlo en cuenta
MIN_VOTOS_SHELF = 2

def detectar_genero(popular_shelves):

    mejor_genero = None
    mejor_count = 0

    for shelf in popular_shelves:
        nombre = shelf["name"].lower().strip()
        count = int(shelf.get("count", 0))

        if count < MIN_VOTOS_SHELF:
            continue

        for patron, categoria in MAPEO_GENEROS.items():
            if patron in nombre:
                if count > mejor_count:
                    mejor_genero = categoria
                    mejor_count = count
                break

    return mejor_genero


def procesar_dataset(ruta_entrada, ruta_salida):
    print(f"Abriendo {ruta_entrada}...")

    # Detectar si es .gz o .json normal
    abrir = gzip.open if ruta_entrada.endswith('.gz') else open

    resultado = []
    sin_genero = 0
    total = 0

    with abrir(ruta_entrada, 'rt', encoding='utf-8') as f:
        for linea in f:
            linea = linea.strip()
            if not linea:
                continue

            try:
                libro = json.loads(linea)
            except json.JSONDecodeError:
                continue

            total += 1
            if total % 50000 == 0:
                print(f"  Procesados: {total:,} libros...")

            shelves = libro.get("popular_shelves", [])
            genero = detectar_genero(shelves)

            similar = libro.get("similar_books", [])

            entrada = {
                "book_id":        libro.get("book_id"),
                "title":          libro.get("title"),
                "genero":         genero,           # None si no se detectó
                "average_rating": libro.get("average_rating"),
                "ratings_count":  libro.get("ratings_count"),
                "tiene_similar":  len(similar) > 0,
                "similar_books":  similar,          # lista vacía si no tiene
                "isbn":           libro.get("isbn"),
                "authors":        libro.get("authors"),
                "descripcion":    libro.get("description"),
                "publisher":      libro.get("publisher"),
                "num_pages":     libro.get("num_pages"),
                "publication_year": libro.get("publication_year")
            }

            if genero is None:
                sin_genero += 1

            resultado.append(entrada)

    print(f"\n--- Resultado ---")
    print(f"  Total libros procesados:        {total:,}")
    print(f"  Con género detectado:           {total - sin_genero:,}")
    print(f"  Sin género (genero = null):     {sin_genero:,}")
    print(f"  Con similar_books:              {sum(1 for l in resultado if l['tiene_similar']):,}")

    # Resumen por género
    por_genero = defaultdict(int)
    for l in resultado:
        if l["genero"]:
            por_genero[l["genero"]] += 1
    print(f"\n--- Libros por género ---")
    for g, n in sorted(por_genero.items(), key=lambda x: -x[1]):
        print(f"  {g}: {n:,}")

    print(f"\nGuardando en {ruta_salida}...")
    with open(ruta_salida, 'w', encoding='utf-8') as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print("¡Listo!")


if __name__ == "__main__":
    ARCHIVO_ENTRADA = "goodreads_books_mystery_thriller_crime.json.gz"   
    ARCHIVO_SALIDA  = "dataset_limpio.json"

    procesar_dataset(ARCHIVO_ENTRADA, ARCHIVO_SALIDA)