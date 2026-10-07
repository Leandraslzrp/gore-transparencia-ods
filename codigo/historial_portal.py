"""
Historial de mediciones del Portal de Transparencia (actualizaciones/portal/).

El recorrido del Portal es automático, así que puede repetirse más seguido que las rondas completas (por ejemplo,
cada mes). Cada recorrido se guarda aquí con su fecha y método, y el visor muestra el más reciente y la evolución.
Los datos de los ODS, que requieren codificación humana, siguen saliendo de la última ronda cerrada.

  registro.csv                       fecha, archivo, metodo, gore_medidos, sha256, nota
  portal_matriz_AAAA-MM-DD.csv       matriz 16 × 15 (codigo, gore, A…M, indice)
  portal_detalle_AAAA-MM-DD.csv      evidencia de cada celda (si existe)
"""

import csv
import re
import shutil
from pathlib import Path

import pandas as pd

from comun import RAIZ, sha256_archivo
from ronda import CATS, codigo_de, indice

HISTORIAL = RAIZ / "actualizaciones" / "portal"
REGISTRO = HISTORIAL / "registro.csv"
CAMPOS = ["fecha", "archivo", "metodo", "gore_medidos", "sha256", "nota"]
FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def leer_registro():
    """Filas de actualizaciones/portal/registro.csv ordenadas por fecha."""
    if not REGISTRO.exists():
        return []
    with open(REGISTRO, encoding="utf-8") as f:
        return sorted(csv.DictReader(f), key=lambda r: r["fecha"])


def registrar(matriz, fecha, metodo, nota="", detalle=None, reemplazar=False):
    """Copia una matriz del Portal al historial y la anota en registro.csv. Devuelve la ruta guardada."""
    if not FECHA.match(fecha):
        raise SystemExit(f"La fecha debe ser AAAA-MM-DD (recibí «{fecha}»).")
    HISTORIAL.mkdir(parents=True, exist_ok=True)
    m = pd.read_csv(matriz, encoding="utf-8-sig")
    if "codigo" not in m.columns:
        m.insert(0, "codigo", m.gore.map(codigo_de))
    falt = [c for c in CATS if c not in m.columns]
    if falt:
        raise SystemExit(f"{matriz}: faltan las columnas {falt}.")
    m = m[["codigo", "gore"] + CATS]
    m["indice"] = indice(m).round(1)
    destino = HISTORIAL / f"portal_matriz_{fecha}.csv"
    filas = [r for r in leer_registro() if r["fecha"] != fecha]
    if destino.exists() and not reemplazar:
        raise SystemExit(f"Ya hay una medición del Portal con fecha {fecha}. Use --reemplazar si quiere sustituirla.")
    m.to_csv(destino, index=False, encoding="utf-8")
    if detalle and Path(detalle).exists():
        shutil.copy(detalle, HISTORIAL / f"portal_detalle_{fecha}.csv")
    filas.append(
        {
            "fecha": fecha,
            "archivo": destino.name,
            "metodo": metodo,
            "gore_medidos": int(m[CATS].notna().all(axis=1).sum()),
            "sha256": sha256_archivo(destino),
            "nota": nota,
        }
    )
    with open(REGISTRO, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, CAMPOS)
        w.writeheader()
        w.writerows(sorted(filas, key=lambda r: r["fecha"]))
    return destino


def mediciones():
    """Lista de (fila del registro, DataFrame indexado por código) en orden cronológico."""
    out = []
    for r in leer_registro():
        f = HISTORIAL / r["archivo"]
        if f.exists():
            out.append((r, pd.read_csv(f, encoding="utf-8", dtype={"codigo": str}).set_index("codigo")))
    return out
