"""
Genera el visor web (docs/index.html). La carpeta docs/ se publica tal cual con GitHub Pages.

Qué muestra y de dónde sale (todo automático):
  Transparencia activa  → la medición más reciente del Portal (actualizaciones/portal/) y su evolución
  Índices del CPLT      → datos/referencia_cplt.csv
  ODS                   → la última ronda cerrada (mediciones/<ronda>/), porque requiere codificación humana

Uso:
  python codigo/visor.py                 # lo más reciente
  python codigo/visor.py --ronda 2026-1  # ODS de una ronda específica
"""

import argparse
import json
from datetime import date
from pathlib import Path

import pandas as pd

from comun import CODIGO, RAIZ, REF_CPLT, cargar_gores
from historial_portal import mediciones
from ods_terminos import ods_mencionados
from ronda import CATS, leer, rondas

MESES = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]


def fecha_larga(iso):
    """AAAA-MM-DD → «7 de octubre de 2026»."""
    a, m, d = iso.split("-")
    return f"{int(d)} de {MESES[int(m) - 1]} de {a}"


def txt(v):
    """Texto vacío para valores faltantes."""
    return "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v)


def construir(r):
    """Reúne en un diccionario los datos que muestra el visor."""
    cplt = pd.read_csv(REF_CPLT, encoding="utf-8-sig", dtype={"codigo": str}).set_index("codigo")
    anios = sorted(int(c.split("_")[1]) for c in cplt.columns if c.startswith("cplt_"))
    hist = mediciones()
    if not hist:  # sin historial: usar la matriz de la ronda
        m = leer(r, "portal").set_index("codigo")
        hist = [({"fecha": "", "metodo": f"ronda {r}", "nota": ""}, m)]
    ods = leer(r, "resumen").set_index("codigo")
    erd = leer(r, "mapa").set_index("codigo")
    men = leer(r, "menciones")
    docs = leer(r, "documentos")
    datos = []
    for g in cargar_gores():
        c, n = g["codigo"], g["gore"]
        serie = []
        for _, m in hist:
            if c in m.index and m.loc[c, CATS].notna().all():
                est = [str(m.loc[c, k]) for k in CATS]
                k = sum(e in ("OK", "EX") for e in est)
                serie.append({"s": round(k / len(CATS) * 100, 1), "k": k, "m": est})
            else:
                serie.append(None)
        ult = next((x for x in reversed(serie) if x), None)
        if ult is None:
            raise SystemExit(f"No hay mediciones del Portal para {n}.")
        o = ods.loc[c]
        lista = []
        for x in men[men.codigo == c].to_dict("records"):
            texto = " ".join(str(x.get(k) or "") for k in ("titulo_o_documento", "justificacion"))
            lista.append(
                {
                    "f": x["fuente"],
                    "t": txt(x.get("titulo_o_documento")),
                    "d": txt(x.get("fecha_o_pagina")),
                    "u": txt(x.get("url")) if str(x.get("url", "")).startswith("http") else "",
                    "c": x["consenso"],
                    "j": txt(x.get("justificacion")),
                    "o": ods_mencionados(texto)["por_numero"],
                }
            )
        cp = docs[(docs.codigo == c) & (docs.fuente == "Cuenta pública")]
        cpd = cp.iloc[0].to_dict() if len(cp) else {}
        datos.append(
            {
                "n": n,
                "code": c,
                "cplt": {
                    str(a): (None if pd.isna(cplt.loc[c, f"cplt_{a}"]) else float(cplt.loc[c, f"cplt_{a}"]))
                    for a in anios
                },
                "s": ult["s"],
                "m": ult["m"],
                "h": serie,
                "wr": int(o.web_retoricas),
                "ws": int(o.web_sustantivas),
                "cp": o.cuenta_publica,
                "erd": o.erd_clasificacion,
                "erdDoc": "" if pd.isna(o.erd_documento) else o.erd_documento,
                "lvl": int(o.erd_nivel),
                "sdg": [int(erd.loc[c, f"ods_{i}"]) for i in range(1, 18)],
                "men": lista,
                "cpDoc": txt(cpd.get("documento")),
                "cpUrl": txt(cpd.get("url")) if str(cpd.get("url", "")).startswith("http") else "",
                "cpNota": txt(cpd.get("nota")),
            }
        )
    portal = [
        {
            "fecha": h["fecha"],
            "larga": fecha_larga(h["fecha"]) if h["fecha"] else h["metodo"],
            "metodo": h["metodo"],
            "nota": h.get("nota", ""),
        }
        for h, _ in hist
    ]
    return datos, anios, portal


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ronda", help="ronda de mediciones/ para los ODS (por defecto, la más reciente)")
    ap.add_argument("--salida", default=str(RAIZ / "docs" / "index.html"))
    a = ap.parse_args()
    todas = rondas()
    if not todas:
        raise SystemExit("No hay rondas en mediciones/. Cierre una con cerrar_ronda.py.")
    r = a.ronda or todas[-1]
    datos, anios, portal = construir(r)
    man = leer(r, "manifiesto")
    meta = {
        "anios": [str(x) for x in anios],
        "portal": portal,
        "fecha_ods": man.get("fecha_ods", ""),
        "ronda": r,
        "generado": fecha_larga(date.today().isoformat()),
    }
    html = (CODIGO / "plantillas" / "visor.html").read_text(encoding="utf-8")
    html = html.replace("__DATA__", json.dumps(datos, ensure_ascii=False)).replace(
        "__META__", json.dumps(meta, ensure_ascii=False)
    )
    Path(a.salida).parent.mkdir(parents=True, exist_ok=True)
    Path(a.salida).write_text(html, encoding="utf-8")
    print(
        f"Visor generado en {a.salida}: Portal al {portal[-1]['larga']} ({len(portal)} mediciones), "
        f"ODS de la ronda {r}."
    )


if __name__ == "__main__":
    main()
