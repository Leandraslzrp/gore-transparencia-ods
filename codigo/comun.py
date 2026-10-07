"""Utilidades compartidas: rutas, configuración de GORE, sesión HTTP cortés y guardado de resultados."""

import csv
import hashlib
import json
import logging
import os
import platform
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

RAIZ = Path(__file__).resolve().parents[1]  # raíz del repositorio (este archivo está en codigo/)
CODIGO = RAIZ / "codigo"
CONFIG = RAIZ / "config"
DATOS = RAIZ / "datos"
REF_CPLT = DATOS / "referencia_cplt.csv"  # índices del CPLT por GORE y año
SALIDAS = RAIZ / "salidas"
CACHE = RAIZ / "cache"
MANUALES = RAIZ / "documentos_manuales"  # PDF descargados a mano: {codigo}_{fuente}.pdf (fuente = cuenta_publica | erd)
for d in (SALIDAS, CACHE, MANUALES):
    d.mkdir(exist_ok=True)


# Identifíquese: los sitios públicos agradecen saber quién consulta y para qué. El correo de contacto se toma de
# la variable de entorno CONTACTO_INVESTIGACION o de config/contacto.txt (una línea); así no hay que editar el código.
def _contacto():
    c = os.environ.get("CONTACTO_INVESTIGACION", "").strip()
    f = CONFIG / "contacto.txt"
    if not c and f.exists():
        lineas = f.read_text(encoding="utf-8").strip().splitlines()
        c = lineas[0].strip() if lineas else ""
    return c or "CAMBIAR@correo.cl"


CONTACTO = _contacto()
AGENTE_ROBOTS = "InvestigacionTransparenciaGORE"  # nombre que se busca en robots.txt (además de «*»)
USER_AGENT = (
    "Mozilla/5.0 (compatible; InvestigacionTransparenciaGORE/1.1; "
    f"estudio academico sobre transparencia activa; contacto: {CONTACTO})"
)
PAUSA_MIN, PAUSA_MAX = 1.0, 2.5  # segundos entre solicitudes al mismo sitio


def ahora():
    """Marca de tiempo ISO en UTC (se guarda en cada registro)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def hoy():
    """Fecha local de hoy en formato AAAA-MM-DD (se usa como etiqueta de las salidas)."""
    return datetime.now().strftime("%Y-%m-%d")


def logger(nombre):
    """Registro de mensajes con hora, nivel y módulo."""
    log = logging.getLogger(nombre)
    if not log.handlers:
        log.setLevel(logging.INFO)
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s", "%H:%M:%S")
        h = logging.StreamHandler()
        h.setFormatter(fmt)
        log.addHandler(h)
        f = logging.FileHandler(SALIDAS / f"{nombre}_{hoy()}.log", encoding="utf-8")
        f.setFormatter(fmt)
        log.addHandler(f)
    return log


def cargar_gores(solo=None):
    """Lee config/gores.csv. `solo` = lista de códigos (AB075…) o nombres para filtrar."""
    with open(CONFIG / "gores.csv", encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    if solo:
        solo = {s.strip().lower() for s in solo}
        filas = [r for r in filas if r["codigo"].lower() in solo or r["gore"].lower() in solo]
    return filas


# ------------------------------------------------------------------ robots.txt
# Por defecto se respeta robots.txt de cada sitio (estándar de scraping ético). Convención usada (la de Google):
# si robots.txt no existe o responde 4xx, todo está permitido; si responde 5xx o no se puede leer, se permite
# pero queda registrado. --ignorar-robots desactiva el control y debe justificarse en el informe de la ronda.
IGNORAR_ROBOTS = False
_ROBOTS = {}
BLOQUEADAS = []  # URL que no se visitaron por robots.txt (se guardan en salidas/robots_bloqueadas_FECHA.csv)


class BloqueadoPorRobots(requests.RequestException):
    """La URL está prohibida por el robots.txt del sitio."""


def _parser_robots(url):
    p = urlparse(url)
    base = f"{p.scheme}://{p.netloc}"
    if base in _ROBOTS:
        return _ROBOTS[base]
    rp = None
    try:
        r = requests.get(base + "/robots.txt", headers={"User-Agent": USER_AGENT}, timeout=20)
        if r.status_code == 200 and "text" in r.headers.get("Content-Type", "text/plain"):
            rp = RobotFileParser()
            rp.parse(r.text.splitlines())
    except requests.RequestException:
        rp = None
    _ROBOTS[base] = rp
    return rp


def robots_permite(url):
    """True si robots.txt permite visitar la URL con nuestro user-agent (o si se pidió ignorarlo)."""
    if IGNORAR_ROBOTS or url.rstrip("/").endswith("/robots.txt"):
        return True
    rp = _parser_robots(url)
    return True if rp is None else rp.can_fetch(AGENTE_ROBOTS, url)


def configurar_robots(ignorar):
    """Activa o desactiva el respeto de robots.txt (por defecto se respeta)."""
    global IGNORAR_ROBOTS
    IGNORAR_ROBOTS = bool(ignorar)


def guardar_bloqueadas(etiqueta):
    """Guarda la lista de páginas que robots.txt no permitió visitar."""
    if BLOQUEADAS:
        guardar_csv(BLOQUEADAS, SALIDAS / f"robots_bloqueadas_{etiqueta}.csv")


class SesionRespetuosa(requests.Session):
    """requests.Session que consulta robots.txt antes de cada GET o HEAD."""

    def request(self, method, url, *args, **kwargs):
        """Igual que requests.Session.request, pero se niega a visitar páginas que robots.txt prohíbe."""
        if method.upper() in ("GET", "HEAD") and not robots_permite(url):
            BLOQUEADAS.append({"url": url, "fecha_utc": ahora()})
            raise BloqueadoPorRobots(f"robots.txt no permite visitar {url}")
        return super().request(method, url, *args, **kwargs)


def sesion():
    """Sesión HTTP con reintentos (errores 429/5xx), user-agent identificado y control de robots.txt."""
    if CONTACTO == "CAMBIAR@correo.cl":
        print(
            "AVISO: falta su correo de contacto. Escríbalo en config/contacto.txt (ver README, paso de configuración).",
            file=sys.stderr,
        )
    s = SesionRespetuosa()
    s.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "es-CL,es;q=0.9"})
    reintentos = Retry(
        total=3, backoff_factor=2, status_forcelist=(429, 500, 502, 503, 504), allowed_methods=("GET", "HEAD")
    )
    s.mount("https://", HTTPAdapter(max_retries=reintentos))
    s.mount("http://", HTTPAdapter(max_retries=reintentos))
    return s


def pausa():
    """Espera entre 1 y 2,5 segundos para no sobrecargar los sitios."""
    time.sleep(random.uniform(PAUSA_MIN, PAUSA_MAX))


def estado_http(s, url, timeout=20):
    """Devuelve el código HTTP de un enlace (HEAD y, si falla, GET sin descargar el cuerpo)."""
    try:
        r = s.head(url, allow_redirects=True, timeout=timeout)
        if r.status_code in (403, 405) or r.status_code >= 500:
            r = s.get(url, allow_redirects=True, timeout=timeout, stream=True)
            r.close()
        return r.status_code
    except requests.RequestException as e:
        return f"error: {type(e).__name__}"


def guardar_csv(filas, ruta, campos=None):
    """Guarda una lista de diccionarios como CSV (UTF-8 con BOM, legible en Excel)."""
    ruta = Path(ruta)
    if not filas:
        ruta.write_text("", encoding="utf-8")
        return ruta
    campos = campos or list(dict.fromkeys(k for f in filas for k in f))
    with open(ruta, "w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig: Excel lo abre bien
        w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        w.writerows(filas)
    return ruta


def guardar_jsonl(registro, ruta):
    """Agrega un registro al final de un archivo JSONL (una línea JSON por registro)."""
    with open(ruta, "a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")


def leer_jsonl(ruta):
    """Lee un archivo JSONL; devuelve una lista vacía si no existe."""
    if not Path(ruta).exists():
        return []
    with open(ruta, encoding="utf-8") as f:
        return [json.loads(linea) for linea in f if linea.strip()]


# ------------------------------------------------------------------ huellas y entorno
def sha256_archivo(ruta):
    """Huella SHA-256 de un archivo: permite comprobar que un documento es exactamente el analizado."""
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def sha256_texto(texto):
    """Huella SHA-256 de un texto."""
    return hashlib.sha256((texto or "").encode("utf-8")).hexdigest()


def entorno():
    """Versión de Python, sistema y librerías clave (se guarda en el manifiesto de cada ronda)."""
    from importlib.metadata import PackageNotFoundError, version

    libs = {}
    for n in (
        "pandas",
        "numpy",
        "scipy",
        "openpyxl",
        "requests",
        "beautifulsoup4",
        "lxml",
        "pdfplumber",
        "matplotlib",
        "pdfminer.six",
        "playwright",
        "pytesseract",
        "pdf2image",
        "Pillow",
    ):
        try:
            libs[n] = version(n)
        except PackageNotFoundError:
            libs[n] = None
    return {"python": sys.version.split()[0], "sistema": platform.platform(), "librerias": libs}
