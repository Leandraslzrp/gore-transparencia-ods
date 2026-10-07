"""
Punto de entrada del proyecto: todas las tareas habituales se corren desde aquí (ver documentacion/PROTOCOLO_RONDAS.md).

RONDA DE MEDICIÓN (tres veces al año)
  1) Recolectar (automático, 2 a 4 horas): CPLT, Portal y ODS en sitios web y documentos
       python ejecutar_todo.py recolectar                  # etiqueta = fecha de hoy
       python ejecutar_todo.py recolectar --solo portal    # un solo paso: cplt | portal | ods
     → salidas/revision_manual_FECHA.xlsx: lo que el código no pudo encontrar o verificar
       (documentacion/PROTOCOLO_REVISION_MANUAL.md)

  2) Revisión manual y planilla de codificación (después de llenar la planilla de revisión)
       python ejecutar_todo.py plantilla --etiqueta 2027-04-10
     → salidas/codificacion_ods_FECHA.xlsx, para que DOS personas codifiquen por separado

  3) Cerrar y analizar (después de codificar y acordar el consenso)
       python ejecutar_todo.py cerrar 2027-1 --etiqueta 2027-04-10 --fecha-scraping "10 de abril de 2027" \\
              --fecha-ods "12 al 20 de abril de 2027"
     → mediciones/2027-1/ (datos con huella SHA-256) y resultados/2027-1/ (análisis y figuras)

OTROS
  python ejecutar_todo.py analizar 2026-1         # rehace el análisis y las figuras de una ronda cerrada
  python ejecutar_todo.py verificar 2026-1        # comprueba que los datos de la ronda no cambiaron
  python ejecutar_todo.py pruebas                 # pruebas automáticas (sin internet)
"""

import argparse
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
CODIGO = RAIZ / "codigo"
sys.path.insert(0, str(CODIGO))

from comun import SALIDAS, hoy  # noqa: E402


def correr(script, *args):
    """Ejecuta un script de codigo/ (o un módulo, si empieza con «-m») desde la raíz del repositorio."""
    destino = [script] if script.startswith("-") else [str(CODIGO / script)]
    print("\n>>>", script, *args, flush=True)
    subprocess.run([sys.executable, *destino, *args], check=True, cwd=RAIZ)


def analizar(ronda):
    """Análisis y figuras de una ronda cerrada."""
    correr("analisis_ronda.py", ronda)
    correr("ods_graficos.py", "--ronda", ronda)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="accion", required=True)
    r = sub.add_parser("recolectar", help="CPLT, Portal y ODS (automático)")
    r.add_argument("--solo", choices=["cplt", "portal", "ods"])
    r.add_argument("--gore", nargs="*", help="códigos de GORE, por ejemplo AB098 AB081")
    r.add_argument("--etiqueta", default=hoy())
    r.add_argument("--completo", action="store_true", help="ODS web: también recorrer el mapa del sitio")
    pl = sub.add_parser("plantilla", help="valida la revisión manual y genera la planilla de codificación")
    pl.add_argument("--etiqueta", required=True)
    pl.add_argument("--sin-revision", action="store_true", help="sin la revisión manual (no recomendado)")
    c = sub.add_parser("cerrar", help="cierra la ronda y la analiza")
    c.add_argument("ronda")
    c.add_argument("--etiqueta", required=True)
    c.add_argument("--codificacion")
    c.add_argument("--fecha-scraping")
    c.add_argument("--fecha-ods")
    c.add_argument("--forzar", action="store_true", help="volver a cerrar una ronda ya cerrada (corrección)")
    sub.add_parser("analizar", help="rehace el análisis y las figuras de una ronda cerrada").add_argument("ronda")
    sub.add_parser("verificar", help="comprueba el manifiesto de una ronda").add_argument("ronda")
    sub.add_parser("pruebas", help="pruebas automáticas")
    a = ap.parse_args()

    if a.accion == "recolectar":
        f, g = a.etiqueta, (["--gore", *a.gore] if a.gore else [])
        if a.solo in (None, "cplt"):
            correr("cplt_informes.py", "resumen")
        if a.solo in (None, "portal"):
            correr("portal_scraping.py", *g, "--etiqueta", f)
            correr("portal_indice.py", str(SALIDAS / f"portal_matriz_{f}.csv"))
        if a.solo in (None, "ods"):
            correr("ods_web.py", *g, "--etiqueta", f, *(["--completo"] if a.completo else []))
            correr("ods_documentos.py", *g, "--etiqueta", f)
            correr("revision_manual.py", "crear", "--etiqueta", f)
            print(
                f"\nSiguiente paso: revisión manual en salidas/revision_manual_{f}.xlsx y luego:"
                f" python ejecutar_todo.py plantilla --etiqueta {f}"
            )
    elif a.accion == "plantilla":
        f = a.etiqueta
        extra = []
        if not a.sin_revision:
            correr("revision_manual.py", "exportar", "--etiqueta", f)
            extra = ["--manual", str(SALIDAS / f"ods_menciones_manuales_{f}.csv")]
        correr(
            "ods_codificacion.py",
            "plantilla",
            "--web",
            str(SALIDAS / f"ods_menciones_web_{f}.csv"),
            "--docs",
            str(SALIDAS / f"ods_pasajes_{f}.csv"),
            "--documentos",
            str(SALIDAS / f"ods_documentos_{f}.csv"),
            "--busquedas",
            str(SALIDAS / f"ods_busquedas_{f}.csv"),
            "--etiqueta",
            f,
            *extra,
        )
        print(f"\nSiguiente paso: dos personas codifican salidas/codificacion_ods_{f}.xlsx.")
    elif a.accion == "cerrar":
        cod = a.codificacion or str(SALIDAS / f"codificacion_ods_{a.etiqueta}.xlsx")
        correr("ods_codificacion.py", "kappa", cod)
        correr(
            "cerrar_ronda.py",
            a.ronda,
            "--codificacion",
            cod,
            "--etiqueta",
            a.etiqueta,
            *(["--fecha-scraping", a.fecha_scraping] if a.fecha_scraping else []),
            *(["--fecha-ods", a.fecha_ods] if a.fecha_ods else []),
            *(["--forzar"] if a.forzar else []),
        )
        analizar(a.ronda)
        print(f"\nListo. Revise resultados/{a.ronda}/; luego publique la versión (documentacion/PUBLICAR.md).")
    elif a.accion == "analizar":
        analizar(a.ronda)
    elif a.accion == "verificar":
        correr("cerrar_ronda.py", "--verificar", a.ronda)
    else:
        correr("-m", "unittest", "discover", "-s", "tests", "-v")


if __name__ == "__main__":
    main()
