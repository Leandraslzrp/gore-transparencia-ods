"""
Búsqueda de menciones ODS en los sitios web de los 16 GORE.

Para cada GORE y cada término núcleo, usa el buscador del propio sitio según su plataforma (columna «motor» de
config/gores.csv) y luego ABRE cada resultado para verificar que el término aparece en el texto (los buscadores
devuelven falsos positivos y a veces solo buscan en títulos). Cuando no hay buscador, recorre todas las noticias.

Motores:
  wordpress          {sitio}/?s={termino}&paged=N   (y, como respaldo, la API /wp-json/wp/v2/)
  wp_api             {sitio}/wp-json/wp/v2/{posts,pages}?search={termino}  (cuando ?s= no filtra)
  prontus            url_busqueda con {termino} y {pagina}
  joomla             url_busqueda con {termino}
  araucania          url_busqueda con {termino} y {pagina0}
  recorrido_ids      url_listado con {id_b64}: recorre identificadores 1…N (Valparaíso)
  recorrido_listado  url_listado con {pagina}: recorre el listado de noticias (Los Lagos)

Uso:
  python codigo/ods_web.py                       # todos los GORE
  python codigo/ods_web.py --gore AB080 --max-ids 900
Salidas: salidas/ods_busquedas_FECHA.csv (una fila por GORE × término: resultados del buscador y verificados)
         salidas/ods_menciones_web_FECHA.csv (una fila por página con al menos un término núcleo verificado)
"""

import argparse
import base64
import gzip
import hashlib
import json
import re
from collections import deque
from urllib.parse import quote_plus, urljoin, urlparse

from bs4 import BeautifulSoup

from comun import (
    CACHE,
    SALIDAS,
    ahora,
    cargar_gores,
    configurar_robots,
    guardar_bloqueadas,
    guardar_csv,
    hoy,
    logger,
    pausa,
    sesion,
    sha256_texto,
)
from ods_terminos import NUCLEO, contar, fragmentos, ods_mencionados

TERMINOS_BUSQUEDA = [
    "ODS",
    "Objetivos de Desarrollo Sostenible",
    "Objetivo de Desarrollo Sostenible",
    "Agenda 2030",
    "ODS 16",
]
MAX_PAGINAS = 60  # páginas de resultados por término (tope de seguridad)
EXCLUIR = re.compile(
    r"/(tag|category|categoria|author|page|feed|wp-json|wp-content)/|#|\.(pdf|jpg|png|zip|docx?)$", re.I
)


def html(http, url):
    """Descarga una página (con pausa cortés) y la devuelve lista para recorrer."""
    r = http.get(url, timeout=40)
    pausa()
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")


def enlaces_resultado(soup, sitio, patron=None):
    """Enlaces a artículos dentro del bloque de resultados (heurística común a varios temas)."""
    host = urlparse(sitio).netloc.replace("www.", "")
    cont = soup.select_one("main") or soup.select_one("#content") or soup.body or soup
    out = []
    for a in cont.select(
        "article a[href], h2 a[href], h3 a[href], .search-result a[href], .result-title a[href], a[href]"
    ):
        u = urljoin(sitio + "/", a["href"])
        if host in urlparse(u).netloc and not EXCLUIR.search(u) and (patron is None or re.search(patron, u)):
            out.append(u.split("?")[0] if "idNot=" not in u else u)
    return list(dict.fromkeys(out))


# ---------- motores ----------
def buscar_wordpress(g, termino, http):
    """Resultados del buscador de un sitio WordPress (?s=término), página por página."""
    base = g["sitio"].rstrip("/")
    urls = []
    for n in range(1, MAX_PAGINAS + 1):
        try:
            soup = html(http, f"{base}/?s={quote_plus(termino)}&paged={n}")
        except Exception:
            break
        nuevos = [u for u in enlaces_resultado(soup, base) if u.rstrip("/") != base and u not in urls]
        if not nuevos or "no se encontr" in soup.get_text(" ").lower():
            break
        urls += nuevos
    return urls or buscar_wp_api(g, termino, http)


def buscar_wp_api(g, termino, http):
    """Resultados de la API de WordPress (entradas y páginas) para un término."""
    base, urls = g["sitio"].rstrip("/"), []
    for tipo in ("posts", "pages"):
        for n in range(1, MAX_PAGINAS + 1):
            r = http.get(
                f"{base}/wp-json/wp/v2/{tipo}",
                params={"search": termino, "per_page": 100, "page": n, "_fields": "link"},
                timeout=40,
            )
            pausa()
            if r.status_code != 200 or not r.json():
                break
            urls += [x["link"] for x in r.json()]
            if n >= int(r.headers.get("X-WP-TotalPages", 1)):
                break
    return list(dict.fromkeys(urls))


def buscar_plantilla(g, termino, http, patron=None, con_paginas=True, pagina0=False):
    """Resultados de un buscador cuya URL se define en config/gores.csv (url_busqueda)."""
    urls = []
    inicio = 0 if pagina0 else 1
    for n in range(inicio, inicio + (MAX_PAGINAS if con_paginas else 1)):
        url = g["url_busqueda"].format(termino=quote_plus(termino), pagina=n, pagina0=n)
        try:
            soup = html(http, url)
        except Exception:
            break
        nuevos = [u for u in enlaces_resultado(soup, g["sitio"], patron) if u not in urls]
        if not nuevos:
            break
        urls += nuevos
    return urls


def recorrer_ids(g, http, max_ids):
    """Valparaíso: detalleNoticia.php?idNot=<id en base64>. Revisa todos los id (no depende del término)."""
    return [g["url_listado"].format(id_b64=base64.b64encode(str(i).encode()).decode()) for i in range(1, max_ids + 1)]


def recorrer_listado(g, http):
    """Enlaces de un listado de noticias (url_listado), página por página."""
    urls = []
    for n in range(1, MAX_PAGINAS + 1):
        try:
            soup = html(http, g["url_listado"].format(pagina=n))
        except Exception:
            break
        nuevos = [u for u in enlaces_resultado(soup, g["sitio"], r"noticia|prensa") if u not in urls]
        if not nuevos:
            break
        urls += nuevos
    return urls


def candidatos(g, termino, http, max_ids):
    """Páginas candidatas para un término, según el tipo de buscador del sitio (columna motor)."""
    m = g["motor"]
    if m == "wordpress":
        return buscar_wordpress(g, termino, http)
    if m == "wp_api":
        return buscar_wp_api(g, termino, http)
    if m == "prontus":
        return buscar_plantilla(g, termino, http, patron=r"/site/(artic|edic)/")
    if m == "joomla":
        return buscar_plantilla(g, termino, http, con_paginas=False)
    if m == "araucania":
        return buscar_plantilla(g, termino, http, patron=r"/noticias/", pagina0=True)
    if m == "recorrido_ids":
        return recorrer_ids(g, http, max_ids)
    if m == "recorrido_listado":
        return recorrer_listado(g, http)
    raise ValueError(f"motor desconocido: {m}")


def texto_de(soup):
    """Texto principal de una página, sin menús, encabezados ni pies."""
    for t in soup(["script", "style", "nav", "header", "footer", "aside", "form"]):
        t.decompose()
    cuerpo = soup.select_one("article") or soup.select_one("main") or soup.body or soup
    titulo = (soup.find("h1") or soup.find("title") or soup).get_text(" ", strip=True)[:200]
    fecha = ""
    for sel in ('meta[property="article:published_time"]', "time[datetime]"):
        e = soup.select_one(sel)
        if e:
            fecha = (e.get("content") or e.get("datetime") or "")[:10]
            break
    return titulo, fecha, cuerpo.get_text(" ", strip=True)


def leer_pagina(http, url):
    """Descarga una página y devuelve su texto principal."""
    return texto_de(html(http, url))


# ---------- recorrido completo por mapa del sitio (sitemap) o, si no hay, por enlaces ----------
CACHE_WEB = CACHE / "web"
CACHE_WEB.mkdir(exist_ok=True)
SITEMAP_EXCLUIR = re.compile(r"(category|categoria|tag|author|attachment|media|product_cat|taxonom)", re.I)
ARTICULO = re.compile(r"noticia|prensa|/20\d\d/|/20\d\d-\d\d-\d\d/|/site/artic/|/articulo|/node/|idNot=", re.I)


def _xml_locs(http, url):
    r = http.get(url, timeout=60)
    pausa()
    if r.status_code != 200:
        return [], []
    contenido = r.content
    if contenido[:2] == b"\x1f\x8b":  # mapas comprimidos (.xml.gz), p. ej. sitios Prontus
        contenido = gzip.decompress(contenido)
    if b"<urlset" not in contenido[:2000] and b"<sitemapindex" not in contenido[:2000]:
        return [], []
    soup = BeautifulSoup(contenido, "xml")
    hijos = [loc.get_text(strip=True) for s in soup.find_all("sitemap") for loc in s.find_all("loc")]
    urls = []
    for u in soup.find_all("url"):
        loc, mod = u.find("loc"), u.find("lastmod")
        if loc:
            urls.append((loc.get_text(strip=True), mod.get_text(strip=True)[:10] if mod else ""))
    return hijos, urls


def candidatos_sitemap(g, http):
    """Páginas listadas en el mapa del sitio (sitemap.xml), para sitios sin buscador útil."""
    base = g["sitio"].rstrip("/")
    cands = []
    if (g.get("url_listado") or "").endswith(".xml"):
        cands.append(g["url_listado"])
    try:
        r = http.get(base + "/robots.txt", timeout=30)
        pausa()
        cands += [
            urljoin(base + "/", linea.split(":", 1)[1].strip())
            for linea in r.text.splitlines()
            if linea.lower().startswith("sitemap:")
        ]
    except Exception:
        pass
    m = re.search(r"search_prontus=([\w-]+)", g.get("url_busqueda") or "")
    if m:  # sitios Prontus
        cands.append(f"{base}/{m.group(1)}/site/sitemap_pags.xml")
    cands += [base + "/sitemap_index.xml", base + "/wp-sitemap.xml", base + "/sitemap.xml"]
    return list(dict.fromkeys(cands))


def recorrer_sitemap(g, http, log, desde="2015-01-01", max_urls=6000):
    """Todas las páginas publicadas según el mapa del sitio. Si no hay mapa, recorre el sitio por enlaces."""
    vistos, pendientes, urls = set(), deque(candidatos_sitemap(g, http)), []
    while pendientes and len(urls) < max_urls:
        sm = pendientes.popleft()
        if sm in vistos or SITEMAP_EXCLUIR.search(sm.rsplit("/", 1)[-1]):
            continue
        vistos.add(sm)
        try:
            hijos, locs = _xml_locs(http, sm)
        except Exception:
            continue
        pendientes.extend(h for h in hijos if h not in vistos)
        urls += [u for u, mod in locs if (not mod or mod >= desde) and not EXCLUIR.search(u)]
    urls = list(dict.fromkeys(urls))[:max_urls]
    if urls:
        log.info("%s: mapa del sitio con %d páginas (desde %s)", g["gore"], len(urls), desde)
        return urls
    log.info("%s: sin mapa del sitio; se recorre el sitio por enlaces", g["gore"])
    return recorrer_enlaces(g, http, max_urls=min(max_urls, 1500))


def recorrer_enlaces(g, http, max_urls=3000):
    """Recorre el sitio siguiendo sus enlaces internos (primero las noticias) y guarda el texto de cada página."""
    base = g["sitio"].rstrip("/")
    host = urlparse(base).netloc.replace("www.", "")
    inicio = [u for u in (g.get("url_listado"), base + "/noticias", base + "/category/noticias", base) if u]
    cola, vistos, urls = deque(inicio), set(), []
    while cola and len(vistos) < max_urls:
        u = cola.popleft()
        if u in vistos:
            continue
        vistos.add(u)
        f = CACHE_WEB / (hashlib.md5(u.encode()).hexdigest() + ".json")
        try:
            soup = html(http, u)
        except Exception:
            f.write_text("null", encoding="utf-8")
            continue
        enlaces = [urljoin(u, a["href"]).split("#")[0] for a in soup.select("a[href]")]
        f.write_text(json.dumps(texto_de(soup), ensure_ascii=False), encoding="utf-8")
        urls.append(u)
        for v in enlaces:
            if host in urlparse(v).netloc and not EXCLUIR.search(v) and v not in vistos:
                (cola.appendleft if ARTICULO.search(v) else cola.append)(v)
    return urls


def leer_pagina_cache(http, url):
    """Como leer_pagina, pero guarda el texto en cache/web/ para retomar un recorrido cortado."""
    f = CACHE_WEB / (hashlib.md5(url.encode()).hexdigest() + ".json")
    if f.exists():
        d = json.loads(f.read_text(encoding="utf-8"))
        return None if d is None else tuple(d)
    try:
        d = leer_pagina(http, url)
    except Exception:
        d = None
    f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return d


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gore", nargs="*")
    ap.add_argument("--max-ids", type=int, default=900, help="tope de identificadores para recorrido_ids")
    ap.add_argument("--etiqueta", default=hoy())
    ap.add_argument(
        "--completo",
        action="store_true",
        help="además del buscador, revisa todas las páginas del mapa del sitio (GORE con recorrer_sitemap=si en gores.csv, o todos con --gore)",
    )
    ap.add_argument("--desde", default="2015-01-01", help="con --completo: solo páginas modificadas desde esta fecha")
    ap.add_argument("--max-urls", type=int, default=6000, help="con --completo: tope de páginas por GORE")
    ap.add_argument(
        "--ignorar-robots", action="store_true", help="no consultar robots.txt (justifíquelo en el informe)"
    )
    a = ap.parse_args()
    configurar_robots(a.ignorar_robots)
    log, http = logger("ods_web"), sesion()
    busquedas, menciones, leidas = [], {}, {}
    for g in cargar_gores(a.gore):
        recorrido = g["motor"].startswith("recorrido")
        terminos = ["(recorrido completo)"] if recorrido else list(TERMINOS_BUSQUEDA)
        if (
            a.completo
            and not recorrido
            and (a.gore or (g.get("recorrer_sitemap") or "").strip().lower() in ("si", "sí"))
        ):
            terminos.append("(mapa del sitio)")
        for termino in terminos:
            try:
                if termino == "(mapa del sitio)":
                    urls = recorrer_sitemap(g, http, log, a.desde, a.max_urls)
                else:
                    urls = candidatos(g, termino, http, a.max_ids)
            except Exception as e:
                log.warning("%s «%s»: búsqueda fallida (%s)", g["gore"], termino, e)
                urls = []
            verificados = 0
            for u in urls:
                if u not in leidas:
                    leidas[u] = leer_pagina_cache(http, u)
                if not leidas[u]:
                    continue
                titulo, fecha, texto = leidas[u]
                c = contar(texto, contexto=False)
                clave = "Objetivos de Desarrollo Sostenible" if termino.startswith("Objetivo") else termino
                completo = recorrido or termino == "(mapa del sitio)"
                if not ((completo and any(c[k] for k in NUCLEO)) or c.get(clave, 0)):
                    continue  # el buscador devolvió la página, pero el término no está en el texto
                verificados += 1
                menciones[u] = {
                    "codigo": g["codigo"],
                    "gore": g["gore"],
                    "fuente": "Sitio web",
                    "url": u,
                    "titulo": titulo,
                    "fecha": fecha,
                    **{f"n_{k}": v for k, v in c.items()},
                    "ods_nombrados": " ".join(map(str, ods_mencionados(texto)["todos"])),
                    "contexto": " | ".join(fragmentos(texto, 220, 3)),
                    "sha256_texto": sha256_texto(texto),
                    "revisado_utc": ahora(),
                }
            busquedas.append(
                {
                    "codigo": g["codigo"],
                    "gore": g["gore"],
                    "motor": g["motor"],
                    "termino": termino,
                    "resultados_buscador": len(urls),
                    "con_termino_verificado": verificados,
                    "fecha_utc": ahora(),
                }
            )
            log.info("%s «%s»: %d resultados, %d verificados", g["gore"], termino, len(urls), verificados)
    guardar_csv(busquedas, SALIDAS / f"ods_busquedas_{a.etiqueta}.csv")
    guardar_csv(list(menciones.values()), SALIDAS / f"ods_menciones_web_{a.etiqueta}.csv")
    guardar_bloqueadas(a.etiqueta)
    log.info("Listo: %d páginas con mención.", len(menciones))


if __name__ == "__main__":
    main()
