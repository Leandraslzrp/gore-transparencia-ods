"""
Revisión manual de una ronda: lo que el código no pudo encontrar o verificar (ver «Revisión manual» en el README).

1) Después de recolectar, crear la planilla de revisión con los casos pendientes:
     python codigo/revision_manual.py crear --etiqueta 2027-04-10
   → salidas/revision_manual_2027-04-10.xlsx con las hojas:
     Pendientes (lo que hay que revisar a mano) · Menciones_manuales (menciones web halladas a mano) ·
     Busquedas_manuales (registro de cada búsqueda hecha a mano)

2) Después de revisar, validar y exportar:
     python codigo/revision_manual.py exportar --etiqueta 2027-04-10
   → salidas/revision_manual_2027-04-10.csv, ods_menciones_manuales_2027-04-10.csv y busquedas_manuales_2027-04-10.csv
   La plantilla de codificación incorpora las menciones manuales (ejecutar_todo.py plantilla).

Casos que se marcan como pendientes:
  · Portal: celdas ER (error o ítem inexistente) y SD (sin datos)
  · Documentos: ERD o cuenta pública «No disponible» o «Solo video»
  · Documentos con poco texto por página (probable imagen escaneada): confirmar con OCR o lectura
  · Sitios web: GORE sin ninguna mención verificada por el código, o con búsquedas fallidas
  · Robots.txt: páginas que el sitio pidió no visitar
  · Control de calidad: muestra al azar (semilla fija) de documentos «Sin mención» para confirmar a mano
"""

import argparse
import random

import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

from comun import SALIDAS, cargar_gores

F = Font(name="Arial", size=10)
FB = Font(name="Arial", size=10, bold=True)
FH = Font(name="Arial", size=10, bold=True, color="FFFFFF")
HD = PatternFill("solid", fgColor="1F4E79")
AM = PatternFill("solid", fgColor="FFF2CC")
RESULTADOS = [
    "Confirmado (sin cambios)",
    "Encontrado a mano",
    "Corregido",
    "No disponible (confirmado por 2)",
    "Solo video",
    "No aplica",
]
MIN_CAR_PAG = 300
MUESTRA_SIN_MENCION = 5


def _leer(nombre, e):
    f = SALIDAS / f"{nombre}_{e}.csv"
    return pd.read_csv(f, encoding="utf-8-sig", dtype={"codigo": str}) if f.exists() else None


def pendientes(e):
    """Lista de casos que una persona debe revisar a mano (ver «Revisión manual» en el README)."""
    filas, gores = [], {g["gore"]: g["codigo"] for g in cargar_gores()}
    m = _leer("portal_matriz", e)
    if m is not None:
        for r in m.to_dict("records"):
            for c, v in r.items():
                if v in ("ER", "SD"):
                    filas.append(
                        (
                            "Portal",
                            gores.get(r["gore"], ""),
                            r["gore"],
                            f"Categoría {c}: {v}",
                            "Abrir la ficha del GORE en el Portal y confirmar el estado; captura de pantalla si cambia",
                        )
                    )
    d = _leer("ods_documentos", e)
    if d is not None:
        for r in d.to_dict("records"):
            if r.get("estado") in ("No disponible", "Solo video"):
                filas.append(
                    (
                        "Documento",
                        r["codigo"],
                        r["gore"],
                        f"{r['fuente']}: {r['estado']}",
                        "Buscar en el sitio (secciones, noticias, visores embebidos, video); si se halla, guardar PDF en documentos_manuales/",
                    )
                )
            elif pd.notna(r.get("caracteres_por_pagina")) and r["caracteres_por_pagina"] < MIN_CAR_PAG:
                filas.append(
                    (
                        "Documento",
                        r["codigo"],
                        r["gore"],
                        f"{r['fuente']}: {int(r['caracteres_por_pagina'])} caracteres por página",
                        "Probable imagen escaneada: confirmar que el OCR leyó el texto o revisar a mano los términos",
                    )
                )
        sin = d[d.estado == "Sin mención"].to_dict("records")
        random.seed(2026)
        for r in random.sample(sin, min(MUESTRA_SIN_MENCION, len(sin))):
            filas.append(
                (
                    "Control de calidad",
                    r["codigo"],
                    r["gore"],
                    f"{r['fuente']}: «Sin mención» (muestra al azar)",
                    "Buscar a mano los términos en el documento (Ctrl+F) y confirmar que no aparecen",
                )
            )
    b = _leer("ods_busquedas", e)
    if b is not None:
        tot = b.groupby(["codigo", "gore"]).con_termino_verificado.sum()
        for (c, g), v in tot.items():
            if v == 0:
                filas.append(
                    (
                        "Sitio web",
                        c,
                        g,
                        "El código no verificó ninguna mención",
                        "Búsqueda dirigida (buscador del sitio, Google site:, sección noticias) con los términos del protocolo",
                    )
                )
    rb = _leer("robots_bloqueadas", e)
    if rb is not None:
        for r in rb.to_dict("records"):
            filas.append(
                (
                    "Robots.txt",
                    "",
                    "",
                    r["url"],
                    "Revisar a mano si la página es pública y relevante; no forzar el recorrido",
                )
            )
    return pd.DataFrame(filas, columns=["Tipo", "Código", "GORE", "Caso", "Qué revisar"])


def encabezado(ws, cols, anchos, fila=1):
    """Escribe una fila de encabezado con formato y fija el ancho de las columnas."""
    for j, (c, w) in enumerate(zip(cols, anchos), 1):
        x = ws.cell(fila, j, c)
        x.font = FH
        x.fill = HD
        x.alignment = Alignment(wrap_text=True, vertical="center")
        ws.column_dimensions[x.column_letter].width = w


def crear(a):
    """Comando «crear»: genera salidas/revision_manual_FECHA.xlsx."""
    p = pendientes(a.etiqueta)
    wb = Workbook()
    ws = wb.active
    ws.title = "Pendientes"
    cols = list(p.columns) + [
        "Resultado",
        "Evidencia (URL o archivo)",
        "Revisor 1",
        "Fecha",
        "Revisor 2 (confirmación)",
        "Nota",
    ]
    encabezado(ws, cols, [16, 8, 18, 34, 55, 24, 45, 16, 11, 18, 40])
    for i, r in enumerate(p.itertuples(index=False), 2):
        for j, v in enumerate(r, 1):
            ws.cell(i, j, v).font = F
        for j in range(6, 12):
            ws.cell(i, j).fill = AM
            ws.cell(i, j).font = F
    dv = DataValidation(type="list", formula1='"' + ",".join(RESULTADOS) + '"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"F2:F{max(2, len(p) + 1)}")
    ws.freeze_panes = "B2"
    ws.auto_filter.ref = f"A1:K{max(2, len(p) + 1)}"

    ws = wb.create_sheet("Menciones_manuales")
    cols = [
        "Código",
        "GORE",
        "URL",
        "Título",
        "Fecha de la página",
        "Términos encontrados",
        "Cómo se encontró",
        "Revisor",
        "Fecha revisión",
    ]
    encabezado(ws, cols, [9, 18, 50, 45, 14, 26, 40, 16, 13])

    ws = wb.create_sheet("Busquedas_manuales")
    cols = [
        "Código",
        "GORE",
        "Dónde se buscó",
        "Consulta exacta",
        "Resultados",
        "Con mención verificada",
        "Revisor",
        "Fecha",
        "Nota",
    ]
    encabezado(ws, cols, [9, 18, 30, 45, 11, 13, 16, 12, 40])
    out = SALIDAS / f"revision_manual_{a.etiqueta}.xlsx"
    wb.save(out)
    print(f"Planilla de revisión: {out} ({len(p)} casos pendientes)")
    if len(p):
        print(p.Tipo.value_counts().to_string())


def _hoja(wb, nombre):
    ws = wb[nombre]
    filas = list(ws.iter_rows(min_row=1, values_only=True))
    df = pd.DataFrame(filas[1:], columns=filas[0])
    return df[df.iloc[:, :3].notna().any(axis=1)]


def exportar(a):
    """Comando «exportar»: valida la planilla completada y la guarda como CSV."""
    f = SALIDAS / f"revision_manual_{a.etiqueta}.xlsx"
    if not f.exists():
        raise SystemExit(f"No existe {f}. Primero: python codigo/revision_manual.py crear --etiqueta {a.etiqueta}")
    wb = load_workbook(f, data_only=True)
    pend, men, bus = _hoja(wb, "Pendientes"), _hoja(wb, "Menciones_manuales"), _hoja(wb, "Busquedas_manuales")
    errores = []
    sin = pend[pend["Resultado"].isna()]
    if len(sin):
        errores.append(f"{len(sin)} casos pendientes sin Resultado")
    nd = pend[pend["Resultado"].astype(str).str.startswith("No disponible")]
    falta2 = nd[nd["Revisor 2 (confirmación)"].isna()]
    if len(falta2):
        errores.append(
            f"{len(falta2)} casos «No disponible» sin la confirmación del Revisor 2: "
            + ", ".join(falta2["GORE"].astype(str))
        )
    enc = pend[pend["Resultado"].isin(["Encontrado a mano", "Corregido"]) & pend["Evidencia (URL o archivo)"].isna()]
    if len(enc):
        errores.append(f"{len(enc)} casos encontrados o corregidos sin evidencia (URL o archivo)")
    mal = men[men["URL"].isna() | men["Términos encontrados"].isna()]
    if len(mal):
        errores.append(f"{len(mal)} menciones manuales sin URL o sin términos")
    if errores and not a.forzar:
        raise SystemExit(
            "Revisión incompleta:\n  - "
            + "\n  - ".join(errores)
            + "\n(complete la planilla, o use --forzar y explíquelo en CHANGELOG.md)"
        )
    pend.to_csv(SALIDAS / f"revision_manual_{a.etiqueta}.csv", index=False, encoding="utf-8")
    m = pd.DataFrame(
        {
            "codigo": men["Código"],
            "gore": men["GORE"],
            "url": men["URL"],
            "titulo": men["Título"],
            "fecha": men["Fecha de la página"],
            "terminos": men["Términos encontrados"],
            "como_se_encontro": men["Cómo se encontró"],
            "revisor": men["Revisor"],
            "fecha_revision": men["Fecha revisión"],
        }
    )
    m.to_csv(SALIDAS / f"ods_menciones_manuales_{a.etiqueta}.csv", index=False, encoding="utf-8")
    bus.to_csv(SALIDAS / f"busquedas_manuales_{a.etiqueta}.csv", index=False, encoding="utf-8")
    print(f"Exportado: {len(pend)} casos revisados, {len(m)} menciones manuales, {len(bus)} búsquedas manuales.")
    if len(pend):
        print(pend["Resultado"].value_counts().to_string())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="accion", required=True)
    c = sub.add_parser("crear")
    c.add_argument("--etiqueta", required=True)
    x = sub.add_parser("exportar")
    x.add_argument("--etiqueta", required=True)
    x.add_argument("--forzar", action="store_true")
    a = ap.parse_args()
    crear(a) if a.accion == "crear" else exportar(a)


if __name__ == "__main__":
    main()
