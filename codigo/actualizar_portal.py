"""
Actualiza la medición del Portal de Transparencia y el visor, sin esperar a una ronda completa.

  python codigo/actualizar_portal.py                      # recorre el Portal hoy, guarda en actualizaciones/portal/ y regenera el visor
  python codigo/actualizar_portal.py --publicar           # además sube el resultado a GitHub (git add, commit y push)
  python codigo/actualizar_portal.py --matriz salidas/portal_matriz_2026-10-06.csv   # registra un recorrido ya hecho

Cada medición queda con su fecha, su huella SHA-256 y el método en actualizaciones/portal/registro.csv.
Los resultados ODS del visor siguen siendo los de la última ronda cerrada (necesitan codificación humana).
"""

import argparse
import subprocess
import sys

from comun import CODIGO, RAIZ, SALIDAS, hoy
from historial_portal import registrar


def correr(*args, **kw):
    """Muestra y ejecuta un comando desde la raíz del repositorio; se detiene si falla."""
    print("\n>>>", " ".join(map(str, args)), flush=True)
    return subprocess.run(list(map(str, args)), check=True, cwd=RAIZ, **kw)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fecha", default=hoy(), help="fecha de la medición, AAAA-MM-DD (por defecto, hoy)")
    ap.add_argument("--matriz", help="registrar una matriz ya generada en vez de recorrer el Portal")
    ap.add_argument("--metodo", default="portal_scraping.py (automático)")
    ap.add_argument("--nota", default="")
    ap.add_argument("--reemplazar", action="store_true", help="sustituir una medición de la misma fecha")
    ap.add_argument("--publicar", action="store_true", help="git add + commit + push al terminar")
    a = ap.parse_args()
    matriz = a.matriz
    if not matriz:
        correr(sys.executable, CODIGO / "portal_scraping.py", "--etiqueta", a.fecha)
        matriz = SALIDAS / f"portal_matriz_{a.fecha}.csv"
    destino = registrar(
        matriz, a.fecha, a.metodo, a.nota, detalle=SALIDAS / f"portal_detalle_{a.fecha}.csv", reemplazar=a.reemplazar
    )
    print(f"Medición del Portal guardada en {destino.relative_to(RAIZ)}")
    correr(sys.executable, CODIGO / "visor.py")
    if a.publicar:
        correr("git", "add", "actualizaciones/portal", "docs/index.html")
        r = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=RAIZ)
        if r.returncode == 0:
            print("No hay cambios que publicar.")
            return
        correr("git", "commit", "-m", f"Actualización del Portal {a.fecha}")
        correr("git", "push")
        print("Publicado. GitHub Pages actualiza el visor en 1 o 2 minutos.")


if __name__ == "__main__":
    main()
