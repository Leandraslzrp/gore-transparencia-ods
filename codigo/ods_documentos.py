"""
Revisión ODS de documentos (última cuenta pública y ERD vigente de cada GORE).

1. Descarga cada PDF de config/gores.csv (columnas url_cuenta_publica y url_erd) a cache/.
   Si no hay URL o la descarga falla, busca el archivo en documentos_manuales/{codigo}_{fuente}.pdf
   (fuente = cuenta_publica | erd). Así se incorporan PDF obtenidos a mano (Google Drive, .zip, etc.).
2. Extrae el texto página a página (pdftotext de Poppler si está instalado; si no, pdfplumber). Si el promedio es menor a 300 caracteres por página, el
   documento se trata como imagen y se aplica OCR (Tesseract, idioma español).
3. Cuenta los términos por documento y guarda cada página con un término núcleo como «pasaje» a codificar,
   con un extracto de contexto y los ODS (1–17) y metas que nombra.

Uso:
  python codigo/ods_documentos.py                    # todos
  python codigo/ods_documentos.py --gore AB089       # un GORE
  python codigo/ods_documentos.py --sin-ocr          # no aplica OCR (más rápido)
Salidas: salidas/ods_documentos_FECHA.csv (una fila por documento) y salidas/ods_pasajes_FECHA.csv (una por página).
"""

import argparse
import hashlib
import io
import re
import shutil
import subprocess
import zipfile
from urllib.parse import unquote, urljoin, urlparse

import pdfplumber
from bs4 import BeautifulSoup

from comun import (
    CACHE,
    MANUALES,
    SALIDAS,
    BloqueadoPorRobots,
    ahora,
    cargar_gores,
    configurar_robots,
    guardar_bloqueadas,
    guardar_csv,
    hoy,
    logger,
    pausa,
    sesion,
    sha256_archivo,
)
from ods_terminos import NUCLEO, contar, fragmentos, ods_mencionados, sin_tildes, tiene_nucleo

UMBRAL_OCR = 300  # caracteres por página bajo los cuales el PDF se considera en imágenes
FUENTES = {"cuenta_publica": ("Cuenta pública", "url_cuenta_publica"), "erd": ("ERD", "url_erd")}


PALABRAS = {
    "cuenta_publica": re.compile(r"cuenta[\s_-]*publica", re.I),
    "erd": re.compile(r"estrategia[\s_-]*regional|(?<![a-z])erd(?![a-z])", re.I),
}


def _es_pdf(b):
    return b[:4] == b"%PDF"


def _drive_directo(url):
    m = re.search(r"drive\.google\.com/(?:file/d/|open\?id=|uc\?id=)([\w-]+)", url)
    return f"https://drive.usercontent.google.com/download?id={m.group(1)}&export=download&confirm=t" if m else url


def _bajar(http, url, log):
    """Descarga con requests y, si el sitio rechaza programas, con un navegador real (Playwright)."""
    try:
        r = http.get(url, timeout=180)
        if r.ok and (_es_pdf(r.content) or r.content[:2] == b"PK"):
            return r.content, r
        primera = r
    except BloqueadoPorRobots as e:
        log.warning("   %s", e)
        return None, None
    except Exception:
        primera = None
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            nav = p.chromium.launch()
            ctx = nav.new_context(accept_downloads=True)
            pagina = ctx.new_page()
            try:  # visitar primero el sitio para obtener sus cookies
                u = urlparse(url)
                pagina.goto(f"{u.scheme}://{u.netloc}/", timeout=60000)
            except Exception:
                pass
            resp = ctx.request.get(
                url, timeout=180000, headers={"Referer": f"{urlparse(url).scheme}://{urlparse(url).netloc}/"}
            )
            cuerpo = resp.body() if resp.ok else b""
            nav.close()
        if _es_pdf(cuerpo) or cuerpo[:2] == b"PK":
            log.info("   descargado con navegador: %s", url[:90])
            return cuerpo, primera
    except Exception as e:
        log.warning("   navegador no pudo descargar %s (%s)", url[:90], type(e).__name__)
    return None, primera


def _pdf_de_zip(contenido, destino):
    """Extrae del .zip el PDF más reciente (año más alto en el nombre; si empatan, el más grande)."""
    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        pdfs = [n for n in z.namelist() if n.lower().endswith(".pdf")]
        if not pdfs:
            return None

        def clave(n):
            anios = [int(a) for a in re.findall(r"20\d\d", n)]
            return (max(anios) if anios else 0, z.getinfo(n).file_size)

        mejor = max(pdfs, key=clave)
        destino.write_bytes(z.read(mejor))
        return mejor


def _pdf_en_pagina(http, url, clave, log):
    """Si la URL es una página web, busca en ella el enlace al PDF del documento (el de año más reciente)."""
    try:
        r = http.get(url, timeout=60)
        pausa()
        soup = BeautifulSoup(r.content, "lxml")
    except Exception:
        return None
    cands = []
    for a in soup.select("a[href]"):
        href = urljoin(url, a["href"])
        texto = sin_tildes(a.get_text(" ", strip=True) + " " + unquote(href))
        if (href.lower().split("?")[0].endswith(".pdf") or "drive.google" in href) and PALABRAS[clave].search(texto):
            anios = [int(x) for x in re.findall(r"20\d\d", texto)]
            cands.append((max(anios) if anios else 0, href))
    if not cands and PALABRAS[clave].search(
        sin_tildes(unquote(url) + " " + (soup.title.get_text() if soup.title else ""))
    ):
        # la página misma es de la cuenta pública / ERD: vale cualquier PDF enlazado (el de año más reciente)
        for a in soup.select("a[href]"):
            href = urljoin(url, a["href"])
            if href.lower().split("?")[0].endswith(".pdf"):
                texto = sin_tildes(a.get_text(" ", strip=True) + " " + unquote(href))
                anios = [int(x) for x in re.findall(r"20\d\d", texto)]
                cands.append((max(anios) if anios else 0, href))
    if cands:
        href = max(cands)[1]
        log.info("   PDF encontrado en la página: %s", href[:100])
        return href
    return None


MIN_PAGINAS = {"cuenta_publica": 5, "erd": 20}  # menos páginas = folleto o resumen, no el documento


def _paginas_pdf(ruta):
    try:
        import pdfplumber

        with pdfplumber.open(ruta) as pdf:
            return len(pdf.pages)
    except Exception:
        return 0


def _valido(ruta, clave, g, log):
    n = _paginas_pdf(ruta)
    if n < MIN_PAGINAS[clave]:
        log.warning(
            "%s %s: PDF descartado, tiene %d páginas (mínimo %d): %s",
            g["gore"],
            clave,
            n,
            MIN_PAGINAS[clave],
            ruta.name,
        )
        return False
    return True


def obtener_pdf(g, clave, http, log, descargar=True):
    """Devuelve (ruta, origen) del PDF o (None, motivo).
    La columna de gores.csv puede traer: la URL de un PDF, de un .zip, de Google Drive o de una página web que
    enlaza al documento; o varias separadas por « | » (se usa la primera que funcione)."""
    manual = MANUALES / f"{g['codigo']}_{clave}.pdf"
    celda = (g.get(FUENTES[clave][1]) or "").strip() if descargar else ""
    urls = [u.strip() for u in celda.split("|") if u.strip().startswith("http")]
    for url in urls:
        destino = CACHE / f"{g['codigo']}_{clave}_{hashlib.md5(url.encode()).hexdigest()[:8]}.pdf"
        if destino.exists() and destino.stat().st_size > 1000 and _valido(destino, clave, g, log):
            return destino, url
        objetivo = _drive_directo(url)
        es_archivo = (
            re.search(r"\.(pdf|zip)(\?|$)", url.lower())
            or "drive.google" in url
            or "asocfile" in url
            or "/docs/" in url
        )
        if not es_archivo:
            objetivo = _pdf_en_pagina(http, url, clave, log)
            if not objetivo:
                log.warning("%s %s: la página no enlaza un PDF reconocible: %s", g["gore"], clave, url[:90])
                continue
            objetivo = _drive_directo(objetivo)
        contenido, r = _bajar(http, objetivo, log)
        pausa()
        if contenido is None:
            log.warning("%s %s: la URL no entregó un PDF (HTTP %s)", g["gore"], clave, getattr(r, "status_code", "—"))
            continue
        if contenido[:2] == b"PK":
            nombre = _pdf_de_zip(contenido, destino)
            if not nombre:
                log.warning("%s %s: el .zip no contiene PDF", g["gore"], clave)
                continue
            log.info("   del .zip se usó: %s", nombre)
            if _valido(destino, clave, g, log):
                return destino, f"{url} → {nombre}"
            continue
        destino.write_bytes(contenido)
        if _valido(destino, clave, g, log):
            return destino, objetivo if objetivo != url else url
    if manual.exists() and manual.stat().st_size > 1000:
        return manual, "archivo manual"
    if celda.lower().startswith("video"):
        return None, f"solo video, sin documento: {celda[:150]}"
    return None, ("sin URL de PDF" if not urls else f"no descargable: {celda[:150]}")


def texto_paginas(ruta, ocr=True, log=None):
    """Lista de textos por página. Aplica OCR si el PDF es mayoritariamente imagen."""
    if shutil.which("pdftotext"):  # Poppler: mucho más rápido en documentos largos; separa páginas con \f
        salida = subprocess.run(["pdftotext", "-enc", "UTF-8", str(ruta), "-"], capture_output=True, timeout=600)
        paginas = salida.stdout.decode("utf-8", "ignore").split("\f")
        if paginas and not paginas[-1].strip():
            paginas = paginas[:-1]
    else:
        with pdfplumber.open(ruta) as pdf:
            paginas = [(p.extract_text() or "") for p in pdf.pages]
    promedio = sum(len(t) for t in paginas) / max(len(paginas), 1)
    metodo = "texto"
    if ocr and promedio < UMBRAL_OCR:
        try:
            import pytesseract
            from pdf2image import convert_from_path

            n, paginas = len(paginas), []
            for i in range(1, n + 1):  # una página a la vez: poca memoria
                img = convert_from_path(str(ruta), dpi=150, first_page=i, last_page=i)[0]
                paginas.append(pytesseract.image_to_string(img, lang="spa"))
            metodo = "OCR"
        except Exception as e:
            metodo = f"texto (OCR no disponible: {type(e).__name__})"
            if log:
                log.warning("OCR no disponible para %s: %s", ruta.name, e)
    return paginas, promedio, metodo


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gore", nargs="*")
    ap.add_argument("--sin-ocr", action="store_true")
    ap.add_argument("--solo-manuales", action="store_true", help="no descarga: usa solo documentos_manuales/")
    ap.add_argument("--etiqueta", default=hoy())
    ap.add_argument(
        "--ignorar-robots", action="store_true", help="no consultar robots.txt (justifíquelo en el informe)"
    )
    a = ap.parse_args()
    configurar_robots(a.ignorar_robots)
    log, http = logger("ods_documentos"), sesion()
    docs, pasajes = [], []
    for g in cargar_gores(a.gore):
        for clave, (nombre, _) in FUENTES.items():
            ruta, origen = obtener_pdf(g, clave, http, log, descargar=not a.solo_manuales)
            base = {
                "codigo": g["codigo"],
                "gore": g["gore"],
                "fuente": nombre,
                "origen": origen,
                "fecha_revision_utc": ahora(),
            }
            if ruta is None:
                docs.append(
                    {**base, "estado": "Solo video" if str(origen).startswith("solo video") else "No disponible"}
                )
                log.info("%s · %s: no disponible (%s)", g["gore"], nombre, origen)
                continue
            paginas, prom, metodo = texto_paginas(ruta, ocr=not a.sin_ocr, log=log)
            total = contar("\n".join(paginas))
            con = [i for i, t in enumerate(paginas, 1) if tiene_nucleo(t)]
            ods_doc = ods_mencionados("\n".join(paginas[i - 1] for i in con)) if con else {"todos": [], "metas": []}
            ods_todo = ods_mencionados("\n".join(paginas))  # incluye tablas de indicadores sin la palabra «ODS»
            docs.append(
                {
                    **base,
                    "archivo": ruta.name,
                    "sha256": sha256_archivo(ruta),
                    "bytes": ruta.stat().st_size,
                    "paginas": len(paginas),
                    "caracteres_por_pagina": round(prom),
                    "metodo": metodo,
                    **{f"n_{k}": v for k, v in total.items()},
                    "paginas_con_termino_nucleo": len(con),
                    "ods_nombrados": " ".join(map(str, ods_doc["todos"])),
                    "metas_citadas": " ".join(ods_doc["metas"]),
                    "ods_candidatos_todo_el_documento": " ".join(map(str, ods_todo["por_numero"])),
                    "estado": "Con mención (codificar pasajes)" if con else "Sin mención",
                }
            )
            for i in con:
                t = paginas[i - 1]
                o = ods_mencionados(t)
                c = contar(t, contexto=False)
                pasajes.append(
                    {
                        "id": f"{g['codigo']}-{clave[:2].upper()}-p{i}",
                        "codigo": g["codigo"],
                        "gore": g["gore"],
                        "fuente": nombre,
                        "pagina": i,
                        "terminos": ", ".join(k for k in NUCLEO if c[k]),
                        "ods_nombrados": " ".join(map(str, o["todos"])),
                        "metas": " ".join(o["metas"]),
                        "contexto": " | ".join(fragmentos(t, 250, 3)),
                    }
                )
            log.info(
                "%s · %s: %d págs (%s), %d páginas con término núcleo",
                g["gore"],
                nombre,
                len(paginas),
                metodo,
                len(con),
            )
    guardar_csv(docs, SALIDAS / f"ods_documentos_{a.etiqueta}.csv")
    guardar_csv(pasajes, SALIDAS / f"ods_pasajes_{a.etiqueta}.csv")
    guardar_bloqueadas(a.etiqueta)
    log.info("Listo: %d documentos, %d pasajes a codificar.", len(docs), len(pasajes))


if __name__ == "__main__":
    main()
