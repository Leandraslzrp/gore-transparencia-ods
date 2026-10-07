"""
Cierra una ronda de medición: pasa el Excel ya codificado y las salidas del scraping al formato estándar
(mediciones/<ronda>/), calcula la fiabilidad entre codificadores y escribe un manifiesto con la huella SHA-256
de cada archivo, las fechas y las versiones del software. Después de cerrar, la ronda no se edita: si hay una
corrección, se vuelve a cerrar y el cambio queda en el manifiesto y en CHANGELOG.md.

  python codigo/cerrar_ronda.py 2027-1 --codificacion salidas/codificacion_ods_2027-04-10.xlsx --etiqueta 2027-04-10

--etiqueta es la fecha (o nombre) que se usó al correr el scraping; con ella se ubican en salidas/:
  portal_matriz_ETIQUETA.csv · portal_detalle_ETIQUETA.csv · ods_menciones_web_ETIQUETA.csv ·
  ods_busquedas_ETIQUETA.csv · ods_documentos_ETIQUETA.csv · ods_pasajes_ETIQUETA.csv · robots_bloqueadas_ETIQUETA.csv
"""

import argparse
import json
import shutil
from datetime import datetime, timezone

import pandas as pd

from comun import CONFIG, RAIZ, SALIDAS, entorno, sha256_archivo
from ronda import ARCHIVOS, CATS, carpeta, codigo_de, fiabilidad, indice, resumen_gore

CRUDOS = [
    "portal_matriz",
    "portal_detalle",
    "ods_menciones_web",
    "ods_busquedas",
    "ods_documentos",
    "ods_pasajes",
    "revision_manual",
    "ods_menciones_manuales",
    "busquedas_manuales",
    "robots_bloqueadas",
]


def manifiesto(ronda, out, extra):
    """Escribe manifiesto.json con la huella SHA-256 y el tamaño de cada archivo de la ronda."""
    archivos = sorted(p for p in out.rglob("*") if p.is_file() and p.name != ARCHIVOS["manifiesto"])
    m = {
        "ronda": ronda,
        "cerrada_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        **extra,
        "entorno": entorno(),
        "archivos": {
            str(p.relative_to(out)).replace("\\", "/"): {"sha256": sha256_archivo(p), "bytes": p.stat().st_size}
            for p in archivos
        },
    }
    (out / ARCHIVOS["manifiesto"]).write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
    return m


def verificar(ronda):
    """Comprueba que ningún archivo de la ronda cambió después de cerrarla."""
    out = carpeta(ronda)
    m = json.loads((out / ARCHIVOS["manifiesto"]).read_text(encoding="utf-8"))
    return [k for k, v in m["archivos"].items() if not (out / k).exists() or sha256_archivo(out / k) != v["sha256"]]


def leer_codificacion(xlsx):
    """Lee la planilla de codificación completada y la convierte al formato estándar de la ronda."""
    men = pd.read_excel(xlsx, sheet_name="Menciones")
    men = men[men["ID"].notna() & men["GORE"].notna()]
    men = pd.DataFrame(
        {
            "id": men["ID"],
            "codigo": men["GORE"].map(codigo_de),
            "gore": men["GORE"],
            "fuente": men["Fuente"],
            "fecha_o_pagina": men["Fecha / página"],
            "titulo_o_documento": "",
            "url": men["Ubicación (URL o documento)"],
            "terminos": men["Términos"],
            "cod1": men["Tipo (codificador 1)"],
            "cod2": men["Tipo (codificador 2)"],
            "consenso": men["Consenso final"],
            "justificacion": men["Justificación cod. 1"],
        }
    )
    sin = men[men.consenso.isna() & (men.cod1 != men.cod2)]
    if len(sin):
        raise SystemExit(
            f"Hay {len(sin)} menciones con desacuerdo y sin consenso: {', '.join(sin.id.astype(str)[:10])}…"
        )
    men["consenso"] = men.consenso.fillna(men.cod1)
    if men.consenso.isna().any():
        raise SystemExit("Hay menciones sin codificar: " + ", ".join(men[men.consenso.isna()].id.astype(str)[:10]))

    dc = pd.read_excel(xlsx, sheet_name="Documentos", dtype={"Código": str})
    dc = pd.DataFrame(
        {
            "codigo": dc["Código"],
            "gore": dc["GORE"],
            "fuente": dc["Fuente"],
            "documento": dc["Archivo / origen"],
            "cod1": dc["Clasificación (cod. 1)"],
            "cod2": dc["Clasificación (cod. 2)"],
            "consenso": dc["Consenso final"],
            "nota": dc["Nota"],
        }
    )
    dc["consenso"] = dc.consenso.fillna(dc.cod1.where(dc.cod1 == dc.cod2))
    if dc.consenso.isna().any():
        raise SystemExit(
            "Documentos sin consenso: " + ", ".join(dc[dc.consenso.isna()].gore + " · " + dc[dc.consenso.isna()].fuente)
        )

    mp = pd.read_excel(xlsx, sheet_name="Mapa_17_ODS", dtype={"Código": str})
    ods = [f"ODS {n}" for n in range(1, 18)]
    con = mp[mp.Fila == "consenso"].copy()
    falt = con[con[ods + ["Nivel (0-3)"]].isna().any(axis=1)]
    if len(falt):
        raise SystemExit("Mapa_17_ODS: falta la fila «consenso» completa de: " + ", ".join(falt.GORE))
    mapa = pd.DataFrame(
        {
            "codigo": con["Código"],
            "gore": con["GORE"],
            "documento": con["Documento ERD"].fillna(""),
            "nivel": con["Nivel (0-3)"].astype(int),
            **{f"ods_{n}": con[f"ODS {n}"].astype(int) for n in range(1, 18)},
        }
    )
    largo = []
    for c in mp[mp.Fila.isin(["cod. 1", "cod. 2"])]["Código"].unique():
        f1 = mp[(mp["Código"] == c) & (mp.Fila == "cod. 1")]
        f2 = mp[(mp["Código"] == c) & (mp.Fila == "cod. 2")]
        for n in range(1, 18):
            largo.append(
                {
                    "codigo": c,
                    "gore": f1.GORE.iloc[0],
                    "ods": n,
                    "cod1": f1[f"ODS {n}"].iloc[0],
                    "cod2": f2[f"ODS {n}"].iloc[0],
                }
            )
    mapa_cod = pd.DataFrame(largo)

    ver = None
    try:
        v = pd.read_excel(xlsx, sheet_name="Muestra_verificacion")
        ver = pd.DataFrame(
            {"gore": v["GORE"], "termino": v["Término"], "cod1": v["Conteo cod. 1"], "cod2": v["Conteo cod. 2"]}
        )
        ver = ver[ver.gore.notna()]
    except (ValueError, KeyError):
        pass
    return men, dc, mapa, mapa_cod, ver


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ronda", nargs="?", help="nombre de la ronda, p. ej. 2027-1 (año-número de ronda)")
    ap.add_argument("--codificacion", help="Excel de codificación ya llenado por los dos codificadores")
    ap.add_argument("--etiqueta", help="etiqueta (fecha) de los archivos de salidas/ de esta ronda")
    ap.add_argument("--fecha-scraping", help="fecha del recorrido del Portal, en texto, p. ej. «10 de abril de 2027»")
    ap.add_argument(
        "--fecha-ods", help="fechas de la búsqueda de los ODS, en texto, p. ej. «12 al 20 de abril de 2027»"
    )
    ap.add_argument("--forzar", action="store_true", help="sobrescribir una ronda ya cerrada (queda registrado)")
    ap.add_argument("--verificar", metavar="RONDA", help="solo comprobar el manifiesto de una ronda cerrada")
    a = ap.parse_args()
    if a.verificar:
        malos = verificar(a.verificar)
        print(
            "Ronda íntegra: todos los archivos coinciden con el manifiesto."
            if not malos
            else "ARCHIVOS MODIFICADOS O AUSENTES:\n  " + "\n  ".join(malos)
        )
        raise SystemExit(1 if malos else 0)
    if not (a.ronda and a.codificacion and a.etiqueta):
        ap.error("indique RONDA, --codificacion y --etiqueta")
    out = carpeta(a.ronda, crear=True)
    if (out / ARCHIVOS["manifiesto"]).exists() and not a.forzar:
        raise SystemExit(
            f"La ronda {a.ronda} ya está cerrada. Use --forzar solo para corregirla (y anótelo en CHANGELOG.md)."
        )
    e = a.etiqueta
    matriz = SALIDAS / f"portal_matriz_{e}.csv"
    if not matriz.exists():
        raise SystemExit(f"Falta {matriz}. ¿Corrió portal_scraping.py con --etiqueta {e}?")

    m = pd.read_csv(matriz, encoding="utf-8-sig")
    m.insert(0, "codigo", m.gore.map(codigo_de))
    m["indice"] = indice(m).round(1)
    if m[CATS].isna().any().any():
        print("AVISO: la matriz del Portal tiene celdas vacías; revise portal_detalle.")

    men, dc, mapa, mapa_cod, ver = leer_codificacion(a.codificacion)
    web = SALIDAS / f"ods_menciones_web_{e}.csv"
    if web.exists():
        w = pd.read_csv(web, encoding="utf-8-sig").set_index("url")
        men["sha256_texto"] = men.url.map(w.sha256_texto) if "sha256_texto" in w else ""
        men["titulo_o_documento"] = men.url.map(w.titulo).fillna("")
    docs_csv = SALIDAS / f"ods_documentos_{e}.csv"
    if docs_csv.exists():
        dd = pd.read_csv(docs_csv, encoding="utf-8-sig", dtype={"codigo": str})
        extra = ["sha256"] + [c for c in dd.columns if c.startswith("n_")] + ["paginas", "url_o_origen"]
        dd["url_o_origen"] = dd.get("origen")
        dc = dc.merge(dd[["codigo", "fuente"] + [c for c in extra if c in dd]], on=["codigo", "fuente"], how="left")

    m.to_csv(out / ARCHIVOS["portal"], index=False, encoding="utf-8")
    men.to_csv(out / ARCHIVOS["menciones"], index=False, encoding="utf-8")
    dc.to_csv(out / ARCHIVOS["documentos"], index=False, encoding="utf-8")
    mapa.to_csv(out / ARCHIVOS["mapa"], index=False, encoding="utf-8")
    mapa_cod.to_csv(out / ARCHIVOS["mapa_cod"], index=False, encoding="utf-8")
    resumen_gore(men, dc, mapa).to_csv(out / ARCHIVOS["resumen"], index=False, encoding="utf-8")
    fia = fiabilidad(men, dc, mapa_cod, ver)
    fia.to_csv(out / ARCHIVOS["fiabilidad"], index=False, encoding="utf-8")
    shutil.copy(CONFIG / "gores.csv", out / "config_gores.csv")
    shutil.copy(a.codificacion, out / "codificacion.xlsx")
    crudos = out / "crudos"
    crudos.mkdir(exist_ok=True)
    for base in CRUDOS:
        for f in SALIDAS.glob(f"{base}_{e}.*"):
            shutil.copy(f, crudos / f.name)
    man = manifiesto(
        a.ronda,
        out,
        {
            "etiqueta_salidas": e,
            "fecha_scraping": a.fecha_scraping or e,
            "fecha_ods": a.fecha_ods or e,
            "forzada": bool(a.forzar),
        },
    )
    print(f"Ronda {a.ronda} cerrada en {out.relative_to(RAIZ)} ({len(man['archivos'])} archivos con huella SHA-256).")
    print(fia.to_string(index=False))
    bajos = fia[(fia.kappa.notna()) & (fia.kappa < 0.6)]
    if len(bajos):
        print("AVISO: κ < 0,60 en", ", ".join(bajos.medida), "→ revise el protocolo de codificación antes de analizar.")


if __name__ == "__main__":
    main()
