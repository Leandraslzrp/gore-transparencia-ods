"""
Índice de disponibilidad, análisis de sensibilidad y comparación entre dos recorridos del Portal.

Uso:
  python codigo/portal_indice.py salidas/portal_matriz_2026-09-25.csv
  python codigo/portal_indice.py salidas/portal_matriz_2026-07-22.csv salidas/portal_matriz_2026-09-25.csv   # compara
  python codigo/portal_indice.py ... --cplt datos/referencia_cplt.csv   # agrega la convergencia con el índice del CPLT
"""

import argparse

import pandas as pd
from scipy import stats

from ronda import CATS, kappa
from ronda import indice as indice_ronda

REGLAS = {  # puntaje por estado; "excluir_ER" saca los errores del denominador
    "base (OK=1, EX=1)": ({"OK": 1, "EX": 1, "SD": 0, "ER": 0}, False),
    "EX = 0": ({"OK": 1, "EX": 0, "SD": 0, "ER": 0}, False),
    "EX = 0,5": ({"OK": 1, "EX": 0.5, "SD": 0, "ER": 0}, False),
    "ER excluidos": ({"OK": 1, "EX": 1, "SD": 0, "ER": 0}, True),
}


def leer(ruta):
    """Lee una matriz del Portal (GORE × categorías A…M)."""
    m = pd.read_csv(ruta, encoding="utf-8-sig")
    col = "gore" if "gore" in m.columns else m.columns[0]
    return m.set_index(col)[CATS]


def indice(m, regla="base (OK=1, EX=1)"):
    """Índice de disponibilidad (0–100) de cada GORE según una de las REGLAS de puntaje."""
    pts, excluir = REGLAS[regla]
    return indice_ronda(m, pts, excluir)


def resumen(m, nombre):
    """Muestra el índice medio con cada regla de puntaje y la frecuencia de cada estado por categoría."""
    print(f"\n=== {nombre} ===")
    for r in REGLAS:
        s = indice(m, r)
        print(f"Índice medio ({r}): {s.mean():.1f} % (DE {s.std():.1f})")
    fr = (
        pd.DataFrame({c: m[c].value_counts() for c in CATS})
        .T.reindex(columns=["OK", "EX", "SD", "ER"])
        .fillna(0)
        .astype(int)
    )
    fr["disponible_%"] = ((fr.OK + fr.EX) / len(m) * 100).round(1)
    print(fr.to_string())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("matrices", nargs="+", help="una o dos matrices (CSV con columnas gore, A…M)")
    ap.add_argument("--cplt", help="CSV con columna gore y cplt (o cplt_AAAA: se usa el año más reciente)")
    a = ap.parse_args()
    ms = [leer(r) for r in a.matrices]
    for r, m in zip(a.matrices, ms):
        resumen(m, r)
    if len(ms) == 2:
        m1, m2 = ms[0], ms[1].reindex(ms[0].index)
        b1 = m1.isin(["OK", "EX"]).astype(int).values.ravel()
        b2 = m2.isin(["OK", "EX"]).astype(int).values.ravel()
        po, k = kappa(b1, b2)
        i1, i2 = indice(m1), indice(m2)
        print(f"\n=== Comparación ===\nCeldas coincidentes (0/1): {po:.1%}; κ = {k:.2f}")
        print(pd.crosstab(m1.values.ravel(), m2.values.ravel(), rownames=["recorrido 1"], colnames=["recorrido 2"]))
        print(
            f"Spearman entre índices: ρ = {stats.spearmanr(i1, i2).statistic:.2f}; "
            f"Wilcoxon p = {stats.wilcoxon(i2, i1).pvalue:.3f}"
        )
    if a.cplt:
        c = pd.read_csv(a.cplt, encoding="utf-8-sig").set_index("gore")
        c = c["cplt"] if "cplt" in c.columns else c[sorted(x for x in c.columns if x.startswith("cplt_"))[-1]]
        i = indice(ms[-1]).reindex(c.index)
        s = stats.spearmanr(i, c)
        d = i - c
        print(
            f"\n=== Convergencia con CPLT ===\nSpearman ρ = {s.statistic:.2f} (p = {s.pvalue:.2f}); "
            f"Bland-Altman: sesgo {d.mean():.1f} p.p., límites {d.mean() - 1.96 * d.std():.1f} a {d.mean() + 1.96 * d.std():.1f}"
        )


if __name__ == "__main__":
    main()
