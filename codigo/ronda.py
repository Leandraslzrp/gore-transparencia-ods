"""
Formato estándar de una ronda de medición (mediciones/<ronda>/) y utilidades compartidas.

Cada ronda queda en su propia carpeta con archivos de nombre fijo, para que cualquier persona pueda repetir
el análisis o comparar rondas sin tocar el código. Ver documentacion/DICCIONARIO_DATOS.md.
"""

import json

import pandas as pd

from comun import RAIZ, cargar_gores

MEDICIONES = RAIZ / "mediciones"
CATS = ["A", "B", "C", "D1", "D2", "D3", "E", "F", "G", "H", "I", "J", "K", "L", "M"]
ODS = [f"ods_{i}" for i in range(1, 18)]
CLASES_DOC = ["Sustantiva", "Retórica", "Sin mención", "No disponible"]
RANGO = {"Sustantiva": 3, "Retórica": 2, "Sin mención": 1, "No disponible": 0}

ARCHIVOS = {
    "portal": "portal_matriz.csv",  # codigo, gore, A…M (OK/EX/SD/ER), indice
    "menciones": "ods_menciones.csv",  # una fila por mención (web o página de documento), con codificación
    "documentos": "ods_documentos.csv",  # una fila por documento (ERD o cuenta pública), con clasificación
    "mapa": "erd_mapa_ods.csv",  # consenso: nivel de la ERD y código 0/1/2 de cada ODS
    "mapa_cod": "erd_mapa_ods_codificadores.csv",  # codificación independiente del mapa (cod. 1 y cod. 2)
    "resumen": "ods_resumen_gore.csv",  # derivado: una fila por GORE con la clasificación de cada fuente
    "fiabilidad": "fiabilidad.csv",
    "manifiesto": "manifiesto.json",
}


def carpeta(ronda, crear=False):
    """Carpeta mediciones/RONDA (la crea si se pide)."""
    c = MEDICIONES / ronda
    if crear:
        c.mkdir(parents=True, exist_ok=True)
    elif not c.exists():
        raise SystemExit(
            f"No existe la ronda «{ronda}» (carpeta {c}). Rondas disponibles: {', '.join(rondas()) or 'ninguna'}"
        )
    return c


def _orden(nombre):
    """Rondas «AAAA-N» (N = 1, 2, 3 en el año) en orden cronológico; otros nombres van al final, por nombre."""
    a, _, n = nombre.partition("-")
    return (0, int(a), int(n), "") if a.isdigit() and n.isdigit() else (1, 0, 0, nombre)


def rondas():
    """Rondas cerradas, de la más antigua a la más reciente."""
    return sorted((p.name for p in MEDICIONES.iterdir() if p.is_dir()), key=_orden) if MEDICIONES.exists() else []


def leer(ronda, clave, obligatorio=True):
    """Lee un archivo estándar de una ronda (ver ARCHIVOS); None si falta y no es obligatorio."""
    f = carpeta(ronda) / ARCHIVOS[clave]
    if not f.exists():
        if obligatorio:
            raise SystemExit(f"Falta {f.relative_to(RAIZ)}. ¿Se cerró la ronda con cerrar_ronda.py?")
        return None
    if f.suffix == ".json":
        return json.loads(f.read_text(encoding="utf-8"))
    return pd.read_csv(f, encoding="utf-8-sig", dtype={"codigo": str})


def codigo_de(nombre):
    """Código del Portal (AB075…) a partir del nombre del GORE, tolerando variantes («Magallanes…», «Metropolitana…»)."""
    n = str(nombre).strip().lower()
    for g in cargar_gores():
        a = g["gore"].lower()
        if n == a or n.startswith(a) or a.startswith(n):
            return g["codigo"]
    raise ValueError(f"GORE no reconocido: {nombre}")


def indice(m, pts=None, excluir_er=False):
    """Índice de disponibilidad del Portal (0–100): porcentaje de las 15 categorías con puntaje 1."""
    pts = pts or {"OK": 1, "EX": 1, "SD": 0, "ER": 0}

    def fila(v):
        v = [x for x in v if not (excluir_er and x == "ER")]
        return sum(pts.get(x, 0) for x in v) / len(v) * 100 if v else float("nan")

    return m[CATS].apply(lambda r: fila(list(r)), axis=1)


def _mejor(docs, fuente):
    """Clasificación más alta de los documentos de una fuente (Sustantiva > Retórica > Sin mención)."""
    x = docs[docs.fuente == fuente].sort_values("r", ascending=False)
    return x.consenso.iloc[0] if len(x) else "No disponible"


def resumen_gore(menciones, documentos, mapa):
    """Una fila por GORE: menciones web, clasificación de la cuenta pública y de la ERD, nivel de la ERD."""
    filas = []
    for g in cargar_gores():
        c = g["codigo"]
        w = menciones[(menciones.codigo == c) & (menciones.fuente == "Sitio web")]
        d = documentos[documentos.codigo == c].copy()
        d["r"] = d.consenso.map(RANGO).fillna(-1)
        mp = mapa[mapa.codigo == c]
        filas.append(
            {
                "codigo": c,
                "gore": g["gore"],
                "web_retoricas": int((w.consenso == "Retórica").sum()),
                "web_sustantivas": int((w.consenso == "Sustantiva").sum()),
                "cuenta_publica": _mejor(d, "Cuenta pública"),
                "erd_clasificacion": _mejor(d, "ERD"),
                "erd_documento": mp.documento.iloc[0] if len(mp) else "",
                "erd_nivel": int(mp.nivel.iloc[0]) if len(mp) and pd.notna(mp.nivel.iloc[0]) else 0,
            }
        )
    return pd.DataFrame(filas)


def kappa(a, b):
    """Acuerdo observado y κ de Cohen entre dos listas de códigos."""
    a, b = pd.Series(list(a)).astype(str), pd.Series(list(b)).astype(str)
    if len(a) == 0:
        return float("nan"), float("nan")
    po = float((a == b).mean())
    pe = sum(float((a == c).mean()) * float((b == c).mean()) for c in set(a) | set(b))
    return po, ((po - pe) / (1 - pe) if pe < 1 else float("nan"))


def fiabilidad(menciones, documentos, mapa_cod, verificacion=None):
    """Acuerdo observado y κ de Cohen entre codificadores. Solo se usan los pares donde ambos codificaron."""
    filas = []

    def agrega(medida, a, b):
        po, k = kappa(a, b)
        filas.append(
            {
                "medida": medida,
                "n": len(list(a)),
                "acuerdo": round(po, 4) if po == po else None,
                "kappa": round(k, 4) if k == k else None,
            }
        )

    par = menciones[menciones.cod1.isin(["Retórica", "Sustantiva"]) & menciones.cod2.isin(["Retórica", "Sustantiva"])]
    agrega("Tipo de mención (Retórica/Sustantiva)", par.cod1, par.cod2)
    d = documentos.dropna(subset=["cod1", "cod2"])
    d = d[(d.cod1.astype(str) != "") & (d.cod2.astype(str) != "")]
    agrega("Clasificación de documentos", d.cod1, d.cod2)
    if mapa_cod is not None and len(mapa_cod):
        m = mapa_cod.dropna(subset=["cod1", "cod2"])
        agrega("Mapa 17 ODS (celdas 0/1/2)", m.cod1.astype(int), m.cod2.astype(int))
    if verificacion is not None and len(verificacion):
        v = verificacion.dropna(subset=["cod1", "cod2"])
        ok = (v.cod1 - v.cod2).abs() <= 1
        filas.append(
            {
                "medida": "Conteos web repetidos coincidentes (±1)",
                "n": len(v),
                "acuerdo": round(float(ok.mean()), 4) if len(v) else None,
                "kappa": None,
            }
        )
    return pd.DataFrame(filas)
