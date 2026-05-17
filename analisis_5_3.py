"""
Caso 5.3 — Distancias entre grafos.

Mide la estabilidad del ranking PageRank conforme crece el tamaño del dataset.
Para varios N, toma una muestra de N libros del dataset_limpio.json, ejecuta
PageRank, y compara el ranking resultante con el ranking del dataset completo
usando la tau de Kendall.

Salida:
  - Tabla por consola
  - Fichero distancia_kendall.csv
  - Gráfica distancia_kendall.png
"""

import csv
import json
import os
import random
import sys

import matplotlib.pyplot as plt
from scipy.stats import kendalltau

import lector
import logica

# ─── Configuración ────────────────────────────────────────────────────────────
DATASET_ORIGINAL = "dataset_limpio.json"
TAMAÑOS = [100, 200, 300, 400, 500, 1000, 2000, 5000]
SEED = 42

# Quitamos el cap de libros por subcategoría para esta prueba: queremos
# trabajar con el catálogo entero sin recortar nada.
lector.MAX_LIBROS_POR_SUBCATEGORIA = 10**9

# ─── Carga y filtrado del dataset original ────────────────────────────────────
print(f"Cargando {DATASET_ORIGINAL}...")
with open(DATASET_ORIGINAL, "r", encoding="utf-8") as f:
    libros_raw = json.load(f)

VALIDOS = set(lector.JERARQUIA.keys())
vistos = set()
libros = []
for l in libros_raw:
    bid = l.get("book_id")
    gen = l.get("genero")
    if not bid or gen not in VALIDOS or bid in vistos:
        continue
    vistos.add(bid)
    libros.append(l)

print(f"  libros válidos únicos: {len(libros)}")

random.seed(SEED)
random.shuffle(libros)

# Limitar TAMAÑOS al máximo disponible
TAMAÑOS = [n for n in TAMAÑOS if n <= len(libros)]


# ─── Función auxiliar: PR sobre una lista de libros ───────────────────────────
def calcular_pr(lista_libros, etiqueta):
    ruta = f"_temp_{etiqueta}.json"
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(lista_libros, f, ensure_ascii=False)
    G, refs = lector.leer_entrada(ruta, simplificar=False)
    ratings_data = lector.leer_likes(ruta)
    valores = logica.version_personalizacion_likes(
        G,
        ratings_data,
        refs,
        user_ratings={},
        user_genre_ratings={},
        debug_mode=False,
        aplicar_prior=True,
    )
    pr = {n: v for n, v in valores.items() if G.out_degree(n) == 0}
    os.remove(ruta)
    return pr


# ─── PR sobre el dataset completo (referencia) ────────────────────────────────
print("\n[ref] Calculando PR sobre el dataset completo...")
pr_full = calcular_pr(libros, "full")
print(f"  → PR computado para {len(pr_full)} libros")

# ─── PR sobre cada subconjunto y comparación ──────────────────────────────────
resultados = []
for N in TAMAÑOS:
    muestra = libros[:N]
    print(f"\n[N={N}] Calculando PR sobre {N} libros...")
    pr_sub = calcular_pr(muestra, str(N))

    ids = list(pr_sub.keys() & pr_full.keys())
    if len(ids) < 2:
        print("  ⚠ menos de 2 libros comunes, saltando")
        continue

    vals_sub = [pr_sub[bid] for bid in ids]
    vals_full = [pr_full[bid] for bid in ids]

    tau, pvalue = kendalltau(vals_sub, vals_full)
    resultados.append((N, tau, pvalue, len(ids)))
    print(f"  libros comunes: {len(ids)}  τ = {tau:.4f}  p = {pvalue:.2e}")


# ─── Tabla ────────────────────────────────────────────────────────────────────
print("\n" + "=" * 50)
print(f"{'N':>6}  {'τ Kendall':>10}  {'p-value':>10}  {'#libros':>8}")
print("-" * 50)
for N, tau, p, n in resultados:
    print(f"{N:>6}  {tau:>10.4f}  {p:>10.2e}  {n:>8}")

# CSV
csv_path = "distancia_kendall.csv"
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["N", "tau_kendall", "p_value", "libros_comparados"])
    for r in resultados:
        w.writerow(r)
print(f"\nCSV guardado en {csv_path}")


# ─── Gráfica ──────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9, 5.5))
xs = [r[0] for r in resultados]
ys = [r[1] for r in resultados]
ax.plot(xs, ys, "o-", linewidth=2, markersize=8, color="#2a6f9c")
ax.set_xlabel("Tamaño del dataset (N libros)")
ax.set_ylabel("τ de Kendall vs ranking completo")
ax.set_title("Estabilidad del ranking PageRank en función del tamaño del dataset")
ax.axhline(y=1.0, color="gray", linestyle="--", alpha=0.4, label="τ = 1 (ranking idéntico)")
ax.axhline(y=0.0, color="red", linestyle=":", alpha=0.4, label="τ = 0 (sin correlación)")
ax.set_ylim(-0.1, 1.1)
ax.grid(True, alpha=0.3)
ax.legend(loc="lower right")
for N, tau, _, _ in resultados:
    ax.annotate(f"{tau:.3f}", (N, tau), textcoords="offset points", xytext=(6, 6), fontsize=8)
plt.tight_layout()
png_path = "distancia_kendall.png"
plt.savefig(png_path, dpi=120)
print(f"Gráfica guardada en {png_path}")
