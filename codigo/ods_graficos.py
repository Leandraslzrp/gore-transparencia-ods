"""
Gráficos de resultados ODS de una ronda cerrada (Figuras 4–6 del paper) y, si hay dos o más rondas, la evolución.

Uso:
  python codigo/ods_graficos.py                 # la ronda más reciente
  python codigo/ods_graficos.py --ronda 2026-1
Salidas en resultados/<ronda>/figuras/: fig4_ods_por_fuente.png, fig5_mapa_ods_erd.png, fig6_ods_por_erd.png
y resultados/evolucion_rondas.png (con ≥ 2 rondas). Se usa siempre el consenso de los codificadores.
"""

import argparse

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch, Rectangle

from comun import RAIZ, cargar_gores
from ronda import indice, leer, rondas

SALIDAS = RAIZ / "resultados"

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})
TINTA, GRIS, REJILLA = "#0b0b0b", "#52514e", "#e2e1dd"
C2, C1, C0 = "#1c5cab", "#86b6ef", "#f0efec"  # azul oscuro, azul claro, neutro (validados para daltonismo)
COLOR = {"Sustantiva": C2, "Retórica": C1, "Sin mención": "#e2e1dd", "No disponible": "#ffffff"}
NIVELES = list(COLOR)


def niveles_por_fuente(r):
    """Nivel de divulgación de los ODS de cada GORE en cada fuente (ERD, cuenta pública, sitio web)."""
    men, res = leer(r, "menciones"), leer(r, "resumen").set_index("codigo")
    out = {"ERD": {}, "Cuenta pública": {}, "Sitio web": {}}
    for g in cargar_gores():
        c, n = g["codigo"], g["gore"]
        out["ERD"][n] = res.loc[c, "erd_clasificacion"]
        out["Cuenta pública"][n] = res.loc[c, "cuenta_publica"]
        w = men[(men.codigo == c) & (men.fuente == "Sitio web")]
        out["Sitio web"][n] = (
            "Sustantiva" if (w.consenso == "Sustantiva").any() else "Retórica" if len(w) else "Sin mención"
        )
    return pd.DataFrame(out)


def fig_fuentes(t, dest):
    """Figura 4: número de GORE por nivel de divulgación en cada fuente."""
    cnt = pd.DataFrame({f: t[f].value_counts() for f in t}).reindex(NIVELES).fillna(0).astype(int)
    fig, ax = plt.subplots(figsize=(7.2, 3.1))
    etiquetas = {
        "ERD": "ERD (planificación)",
        "Cuenta pública": "Cuenta pública (rendición de cuentas)",
        "Sitio web": "Sitio web (comunicación)",
    }
    for i, f in enumerate(cnt.columns):
        izq = 0
        for n in NIVELES:
            v = cnt.loc[n, f]
            if not v:
                continue
            ax.barh(
                i,
                v - 0.08,
                left=izq + 0.04,
                height=0.58,
                color=COLOR[n],
                edgecolor="#8a8984" if n == "No disponible" else COLOR[n],
                hatch="////" if n == "No disponible" else None,
                linewidth=0.8,
            )
            ax.text(
                izq + v / 2,
                i,
                str(v),
                ha="center",
                va="center",
                fontweight="bold",
                color="white" if n == "Sustantiva" else TINTA,
            )
            izq += v
    ax.set_yticks(range(len(cnt.columns)))
    ax.set_yticklabels([etiquetas[c] for c in cnt.columns])
    ax.invert_yaxis()
    ax.set_xlim(0, len(t))
    ax.set_xlabel(f"N.º de GORE (de {len(t)})")
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.xaxis.grid(True, color=REJILLA)
    ax.set_axisbelow(True)
    ax.legend(
        handles=[
            Patch(
                facecolor=COLOR[n],
                edgecolor="#8a8984",
                hatch="////" if n == "No disponible" else None,
                label={"Sustantiva": "Vínculo sustantivo", "Retórica": "Solo mención retórica"}.get(n, n),
            )
            for n in NIVELES
        ],
        ncol=2,
        loc="lower left",
        bbox_to_anchor=(-0.02, 1),
        frameon=False,
        fontsize=8,
    )
    fig.tight_layout()
    fig.savefig(dest / "fig4_ods_por_fuente.png", dpi=300)
    plt.close(fig)


def fig_mapa(r, dest):
    """Figuras 5 y 6: mapa de los 17 ODS en las ERD y número de ERD que vinculan cada ODS."""
    mp = leer(r, "mapa")
    c = mp.set_index("gore")[[f"ods_{n}" for n in range(1, 18)]].fillna(0).astype(int)
    c = c[c.sum(axis=1) > 0]
    if c.empty:
        print("Mapa sin codificar: se omiten las Figuras 5 y 6.")
        return
    fig, ax = plt.subplots(figsize=(7.2, 0.45 * len(c) + 1.2))
    for r, (_, fila) in enumerate(c.iterrows()):
        for k, v in enumerate(fila):
            ax.add_patch(Rectangle((k + 0.05, r + 0.05), 0.9, 0.9, color={0: C0, 1: C1, 2: C2}[v]))
    ax.add_patch(Rectangle((15, -0.08), 1, len(c) + 0.16, fill=False, edgecolor=TINTA, linewidth=1.4))
    ax.set_xlim(0, 17)
    ax.set_ylim(len(c), 0)
    ax.set_xticks(np.arange(17) + 0.5)
    ax.set_xticklabels(range(1, 18))
    ax.set_yticks(np.arange(len(c)) + 0.5)
    ax.set_yticklabels(c.index)
    ax.tick_params(length=0)
    ax.set_xlabel("ODS")
    for s in ax.spines.values():
        s.set_visible(False)
    ax.legend(
        handles=[
            Patch(color=C2, label="Vinculado a eje, objetivo o indicador"),
            Patch(color=C1, label="Solo contexto"),
            Patch(color=C0, label="No nombrado"),
        ],
        ncol=3,
        loc="upper center",
        bbox_to_anchor=(0.45, -0.15),
        frameon=False,
        fontsize=7.5,
    )
    fig.tight_layout()
    fig.savefig(dest / "fig5_mapa_ods_erd.png", dpi=300)
    plt.close(fig)
    # Figura 6: n.º de ERD que vinculan cada ODS
    v2, v1 = (c == 2).sum(), (c == 1).sum()
    orden = sorted(range(17), key=lambda i: (v2.iloc[i], v1.iloc[i]))
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    y = np.arange(17)
    ax.barh(y, [v2.iloc[i] for i in orden], height=0.62, color=C2, label="Vinculado a eje, objetivo o indicador")
    ax.barh(
        y,
        [v1.iloc[i] for i in orden],
        left=[v2.iloc[i] + 0.05 for i in orden],
        height=0.62,
        color=C1,
        label="Solo contexto",
    )
    ax.set_yticks(y)
    ax.set_yticklabels([f"ODS {i + 1}" for i in orden])
    for t in ax.get_yticklabels():
        if t.get_text() == "ODS 16":
            t.set_fontweight("bold")
    ax.set_xlabel("N.º de ERD")
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.xaxis.grid(True, color=REJILLA)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(dest / "fig6_ods_por_erd.png", dpi=300)
    plt.close(fig)


def fig_evolucion(todas):
    """Evolución de los indicadores principales entre rondas (cuando hay más de una)."""
    filas = []
    for r in todas:
        m, mp, men = leer(r, "portal"), leer(r, "mapa"), leer(r, "menciones")
        filas.append(
            {
                "ronda": r,
                "Índice del Portal (media, %)": indice(m).mean(),
                "ERD con vínculo sustantivo (%)": (mp.nivel >= 2).mean() * 100,
                "GORE con mención ODS en la web (%)": men[men.fuente == "Sitio web"].codigo.nunique() / len(m) * 100,
            }
        )
    d = pd.DataFrame(filas).set_index("ronda")
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    for col, color, mk in zip(d.columns, ("#2a78d6", "#eb6834", "#1baf7a"), ("o", "s", "^")):
        ax.plot(range(len(d)), d[col], marker=mk, color=color, label=col, linewidth=1.8)
        ax.annotate(
            f"{d[col].iloc[-1]:.0f}",
            (len(d) - 1, d[col].iloc[-1]),
            xytext=(6, 0),
            textcoords="offset points",
            va="center",
            fontsize=8,
            color=color,
        )
    ax.set_xticks(range(len(d)))
    ax.set_xticklabels(d.index)
    ax.set_ylim(0, 105)
    ax.set_ylabel("%")
    for s_ in ("top", "right"):
        ax.spines[s_].set_visible(False)
    ax.yaxis.grid(True, color=REJILLA)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=8, loc="lower left", bbox_to_anchor=(0, 1), ncol=2)
    fig.tight_layout()
    fig.savefig(SALIDAS / "evolucion_rondas.png", dpi=300)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ronda")
    a = ap.parse_args()
    todas = rondas()
    r = a.ronda or todas[-1]
    dest = SALIDAS / r / "figuras"
    dest.mkdir(parents=True, exist_ok=True)
    t = niveles_por_fuente(r)
    t.to_csv(dest / "ods_nivel_por_gore_y_fuente.csv", encoding="utf-8")
    fig_fuentes(t, dest)
    fig_mapa(r, dest)
    if len(todas) >= 2:
        fig_evolucion(todas)
    print("Figuras guardadas en", dest)


if __name__ == "__main__":
    main()
