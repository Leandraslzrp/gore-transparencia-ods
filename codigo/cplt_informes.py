"""
Informes de fiscalización de transparencia activa del Consejo para la Transparencia (CPLT) para los 16 GORE.

El CPLT publica sus resultados como informes y planillas, no como una API. Por eso este módulo:
  1. guarda los índices de cada año en un solo archivo (datos/referencia_cplt.csv: codigo, gore, cplt_AAAA…),
  2. registra la fuente de cada año (config/cplt_informes.csv) y puede descargar esos archivos,
  3. valida los datos y calcula la evolución entre años (medias, variaciones, Friedman y Wilcoxon).

Uso:
  python codigo/cplt_informes.py resumen                         # valida y resume todos los años
  python codigo/cplt_informes.py agregar 2027 nuevo.csv          # suma un año (CSV con columnas codigo o gore, e indice)
  python codigo/cplt_informes.py descargar                       # guarda los informes listados en config/cplt_informes.csv
"""

import argparse
import itertools
import re

import pandas as pd
from scipy import stats

from comun import CONFIG, DATOS, RAIZ, REF_CPLT, SALIDAS, cargar_gores, hoy, logger, pausa, sesion

ARCHIVO = REF_CPLT
INFORMES = DATOS / "informes_cplt"
log = logger("cplt_informes")


def cargar():
    """Lee datos/referencia_cplt.csv y la lista de años disponibles."""
    df = pd.read_csv(ARCHIVO, encoding="utf-8-sig")
    anios = sorted(int(c.split("_")[1]) for c in df.columns if re.fullmatch(r"cplt_\d{4}", c))
    return df, anios


def validar(df, anios):
    """Comprueba que estén los 16 GORE del config y que los índices estén entre 0 y 100."""
    problemas = []
    esperados = {g["codigo"] for g in cargar_gores()}
    faltan, sobran = esperados - set(df.codigo), set(df.codigo) - esperados
    if faltan:
        problemas.append(f"Faltan GORE: {sorted(faltan)}")
    if sobran:
        problemas.append(f"Códigos que no están en config/gores.csv: {sorted(sobran)}")
    for a in anios:
        c = df[f"cplt_{a}"]
        if c.isna().any():
            problemas.append(f"{a}: valores vacíos en {list(df.gore[c.isna()])}")
        if ((c < 0) | (c > 100)).any():
            problemas.append(f"{a}: valores fuera de 0–100")
    return problemas


def resumen(df, anios):
    """Estadísticos por año, cambios por GORE entre años y pruebas de Friedman y Wilcoxon."""
    cols = [f"cplt_{a}" for a in anios]
    filas = []
    for a, c in zip(anios, cols):
        filas.append(
            {
                "anio": a,
                "media": df[c].mean(),
                "mediana": df[c].median(),
                "minimo": df[c].min(),
                "maximo": df[c].max(),
                "gore_90_o_mas": int((df[c] >= 90).sum()),
            }
        )
    res = pd.DataFrame(filas).round(2)
    var = df[["codigo", "gore"]].copy()
    comparaciones = []
    for a, b in itertools.combinations(anios, 2):
        d = df[f"cplt_{b}"] - df[f"cplt_{a}"]
        var[f"var_{a}_{b}_pp"] = d.round(1)
        w = stats.wilcoxon(df[f"cplt_{a}"], df[f"cplt_{b}"]) if (d != 0).any() else None
        comparaciones.append(
            {
                "comparacion": f"{a} → {b}",
                "media_pp": round(d.mean(), 2),
                "mejoran": int((d > 0).sum()),
                "empeoran": int((d < 0).sum()),
                "wilcoxon_p": round(w.pvalue, 4) if w else None,
            }
        )
    pruebas = pd.DataFrame(comparaciones)
    if len(anios) >= 3:
        fr = stats.friedmanchisquare(*[df[c] for c in cols])
        k, n = len(cols), len(df)
        w_kendall = fr.statistic / (n * (k - 1))
        log.info(
            f"Friedman ({', '.join(map(str, anios))}): χ²({k - 1}) = {fr.statistic:.2f}; p = {fr.pvalue:.4f}; "
            f"W de Kendall = {w_kendall:.2f}"
        )
    return res, var, pruebas


def cmd_resumen(_):
    """Comando «resumen»: valida los datos, compara los años y guarda los resultados en salidas/."""
    df, anios = cargar()
    for p in validar(df, anios):
        log.warning(p)
    res, var, pruebas = resumen(df, anios)
    print("\nÍndice CPLT por año\n", res.to_string(index=False))
    print("\nComparaciones entre años\n", pruebas.to_string(index=False))
    f = hoy()
    res.to_csv(SALIDAS / f"cplt_resumen_{f}.csv", index=False, encoding="utf-8-sig")
    var.to_csv(SALIDAS / f"cplt_variaciones_{f}.csv", index=False, encoding="utf-8-sig")
    pruebas.to_csv(SALIDAS / f"cplt_pruebas_{f}.csv", index=False, encoding="utf-8-sig")
    log.info(f"Guardado en salidas/cplt_*_{f}.csv")


def cmd_agregar(a):
    """Comando «agregar»: suma la columna de un año nuevo desde un CSV."""
    df, anios = cargar()
    nuevo = pd.read_csv(a.archivo, encoding="utf-8-sig")
    clave = "codigo" if "codigo" in nuevo.columns else "gore"
    if "indice" not in nuevo.columns:
        raise SystemExit("El CSV debe tener una columna «indice» y otra «codigo» o «gore».")
    col = f"cplt_{a.anio}"
    df[col] = df[clave].map(nuevo.set_index(clave)["indice"])
    for p in validar(df, anios + [a.anio]):
        log.warning(p)
    df.to_csv(ARCHIVO, index=False, encoding="utf-8")
    log.info(f"Agregado {col} a {ARCHIVO.name} ({df[col].notna().sum()} GORE con valor).")


def cmd_descargar(_):
    """Comando «descargar»: guarda los informes del CPLT listados en config/cplt_informes.csv."""
    INFORMES.mkdir(parents=True, exist_ok=True)
    s = sesion()
    for r in pd.read_csv(CONFIG / "cplt_informes.csv", dtype=str).fillna("").to_dict("records"):
        if not r["url"]:
            log.warning(f"{r['anio']}: sin URL en config/cplt_informes.csv")
            continue
        try:
            resp = s.get(r["url"], timeout=60)
            resp.raise_for_status()
        except Exception as e:
            log.error(f"{r['anio']}: no se pudo descargar ({e})")
            continue
        tipo = resp.headers.get("Content-Type", "")
        ext = ".pdf" if "pdf" in tipo else ".xlsx" if "sheet" in tipo or "excel" in tipo else ".html"
        destino = INFORMES / f"cplt_{r['anio']}{ext}"
        destino.write_bytes(resp.content)
        log.info(f"{r['anio']}: {destino.relative_to(RAIZ)} ({len(resp.content) / 1024:.0f} KB)")
        pausa()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("resumen").set_defaults(f=cmd_resumen)
    p = sub.add_parser("agregar")
    p.add_argument("anio", type=int)
    p.add_argument("archivo")
    p.set_defaults(f=cmd_agregar)
    sub.add_parser("descargar").set_defaults(f=cmd_descargar)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
