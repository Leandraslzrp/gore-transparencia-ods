"""
Recorrido de la sección de Transparencia Activa del Portal de Transparencia del Estado para los 16 GORE.

El Portal está hecho con PrimeFaces (JSF): el contenido cambia con clics que disparan peticiones AJAX, no con
URL propias. Por eso se usa un navegador real (Playwright + Chromium) que hace clic como una persona.

Para cada GORE y cada una de las 15 categorías (artículos 6.° y 7.° de la Ley N.° 20.285):
  1. Abre la ficha del organismo y busca el ítem de la categoría por su nombre (acepta variantes).
  2. Entra al período más reciente (año y luego mes). Si ahí no hay datos, prueba hasta 3 períodos o
     subcarpetas hermanas por nivel.
  3. Registra un estado:
       OK = tabla con al menos 1 registro, o imagen incrustada (organigramas)
       EX = archivo alojado en el Portal o enlace a otro sitio que responde
       SD = sin registros («mostrando 0 de 0 resultados», «Nada que informar») o ítem marcado (*)
       ER = ítem inexistente en la portada, enlace roto o falla del recorrido
     y la evidencia: filas y columnas de la tabla, URL del archivo/enlace con su código HTTP, ruta recorrida
     y mensaje del Portal. No se guarda el contenido de las tablas (hay datos personales de funcionarios).

Uso:
  python codigo/portal_scraping.py                         # 16 GORE, 15 categorías
  python codigo/portal_scraping.py --gore AB098 AB081      # solo algunos GORE
  python codigo/portal_scraping.py --categorias K I        # solo algunas categorías
  python codigo/portal_scraping.py --capturas --visible    # guarda captura de cada celda y muestra el navegador
Salidas (carpeta salidas/): portal_celdas_FECHA.jsonl (una línea por celda), portal_matriz_FECHA.csv (16 × 15)
y portal_detalle_FECHA.csv (evidencia de las 240 celdas).
"""

import argparse
import re
import time
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

from comun import (
    SALIDAS,
    USER_AGENT,
    ahora,
    cargar_gores,
    configurar_robots,
    estado_http,
    guardar_csv,
    guardar_jsonl,
    hoy,
    leer_jsonl,
    logger,
    robots_permite,
    sesion,
)

URL_FICHA = "https://www.portaltransparencia.cl/PortalPdT/directorio-de-organismos-regulados/?org={codigo}"
PAUSA_CLIC = 0.8  # segundos de cortesía después de cada clic
MAX_CLICS = 22  # límite de clics por ítem
HERMANOS = 3  # períodos o subcarpetas alternativos que se prueban por nivel

# Categoría → lista de patrones para el nombre del ítem (se prueba en orden; gana el mejor estado).
CATEGORIAS = {
    "A": ("Estructura orgánica", [r"^Organigrama$", r"Diagrama de Estructura Org"]),
    "B": ("Facultades, funciones y atribuciones", [r"^Facultades, funciones y atribuciones de sus unidades"]),
    "C": ("Marco normativo", [r"^Marco Normativo$"]),
    "D1": ("Personal de planta", [r"^Personal de planta"]),
    "D2": ("Personal a contrata", [r"^Personal a contrata"]),
    "D3": ("Personal a honorarios", [r"honorarios"]),
    "E": (
        "Compras y adquisiciones",
        [
            r"Contrata(ciones|ción) (relativas a|de) bienes inmuebles",
            r"no sometidas al Sistema de Compras",
            r"^Licitaciones",
            r"Sistema de Compras P",
        ],
    ),
    "F": ("Transferencias", [r"Transferencias reguladas por Ley", r"^Otras transferencias"]),
    "G": (
        "Actos con efectos sobre terceros",
        [
            r"^Actos y resoluciones con efectos sobre terceros",
            r"^Actos y resoluciones con efectos sobre terceras personas \(",
        ],
    ),
    "H": ("Trámites", [r"^Trámites ante el", r"^Otros Trámites"]),
    "I": ("Subsidios y beneficios", [r"^Subsidios y Beneficios Propios"]),
    "J": (
        "Participación ciudadana",
        [r"^Mecanismos de participación ciudadana$", r"Mecanismos de participación ciudadana en ejecución"],
    ),
    "K": (
        "Ejecución presupuestaria",
        [
            r"^(Informes? (de )?)?Ejecuci[oó]n presupuestaria$",
            r"Presupuesto Asignado y su Ejecuci",
            r"Balance de Ejecuci[oòó]n Presupuestaria",
        ],
    ),
    "L": ("Auditorías", [r"^Auditorías"]),
    "M": ("Vínculos institucionales", [r"^Entidades en que tenga participación"]),
}
RANGO = {"OK": 3, "EX": 2, "SD": 1, "ER": 0}
MESES = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]
MENSAJE_VACIO = re.compile(
    r"mostrando \d+ de \d+ resultados|Nada que informar|No hay (datos|información|registros)"
    r"[^\n]{0,40}|no se ha informado[^\n]{0,120}",
    re.I,
)
ENCABEZADO = re.compile(
    r"^(Transparencia Activa|Contacto y Oficinas de Atención|Formulario de Solicitud de "
    r"Información|Reclamos|Buscar)$"
)

# JavaScript que se ejecuta en la página: lista los enlaces visibles de <main> y detecta tablas o imágenes.
JS_ENLACES = """() => [...(document.querySelector('main')||document.body).querySelectorAll('a')].map((a,i)=>({
    i, texto:(a.textContent||'').replace(/\\s+/g,' ').trim(), onclick:a.getAttribute('onclick')||'', href:a.href||''}))"""
JS_CONTENIDO = """(base) => { const m=document.querySelector('main')||document.body;
  for (const t of m.querySelectorAll('table')) { const rows=[...t.rows].filter(r=>r.cells.length>=2);
    if (rows.length>=2) return {tipo:'tabla', filas:rows.length-1, columnas:rows[0].cells.length}; }
  const im=[...m.querySelectorAll('img')].filter(i=>!base.includes(i.src) && !/icon\\.png|logo|banner|header|footer/i.test(i.src) && (i.naturalWidth>150||/^data:image/.test(i.src)));
  if (im.length) return {tipo:'imagen', n:im.length, src:(im[0].src||'').slice(0,160)};
  return null; }"""
JS_TEXTO = "() => (document.querySelector('main')||document.body).innerText"
JS_AJAX_LIBRE = "() => !window.PrimeFaces || !PrimeFaces.ajax || PrimeFaces.ajax.Queue.isEmpty()"


def puntaje_periodo(texto):
    """Ordena períodos: primero el año más alto y, dentro del año, el mes más reciente."""
    t = texto.lower()
    y = re.search(r"(20\d\d)", t)
    m = next((i for i, x in enumerate(MESES) if x in t), -1)
    return (int(y.group(1)) * 100 if y else 0) + (m + 1 if m >= 0 else 0)


def es_archivo_o_externo(href, host_portal="www.portaltransparencia.cl"):
    """True si el enlace lleva a un archivo del Portal o a un sitio externo (estado EX)."""
    if not href.startswith("http"):
        return False
    if "/PortalPdT/documents/" in href:
        return True
    host = urlparse(href).netloc
    return host != host_portal and "consejotransparencia" not in host


class Recorrido:
    def __init__(self, page, http, log, url_base=URL_FICHA):
        self.page, self.http, self.log, self.url_base = page, http, log, url_base
        self.host = urlparse(url_base).netloc
        self.ficha = url_base.split("?")[0]
        self.salida_bloqueada = None
        # Si un clic intenta abrir un archivo u otro sitio, se bloquea la navegación y se registra la URL:
        page.route("**/*", self._interceptar)
        page.on("download", lambda d: self._registrar_salida(d.url, cancelar=d))
        page.context.on("page", lambda p: (self._registrar_salida(p.url), p.close()))

    # ---------- intercepción de salidas del Portal ----------
    def _registrar_salida(self, url, cancelar=None):
        self.salida_bloqueada = url
        if cancelar is not None:
            try:
                cancelar.cancel()
            except Exception:
                pass

    def _interceptar(self, route):
        req = route.request
        if req.is_navigation_request() and req.frame == self.page.main_frame and not req.url.startswith(self.ficha):
            self._registrar_salida(req.url)
            return route.abort()
        return route.continue_()

    # ---------- utilidades de página ----------
    def _texto(self):
        try:
            return self.page.evaluate(JS_TEXTO)
        except Exception:  # la página está cambiando (p. ej., un clic intentó abrir un archivo)
            return None

    def _esperar(self, texto_antes, espera_max=10.0):
        """Espera que el contenido cambie y que la cola AJAX de PrimeFaces quede vacía."""
        t0 = time.time()
        while time.time() - t0 < espera_max:
            if self.salida_bloqueada:
                return
            if self._texto() != texto_antes:
                break
            time.sleep(0.25)
        try:
            self.page.wait_for_function(JS_AJAX_LIBRE, timeout=15000)
        except Exception:
            pass
        time.sleep(PAUSA_CLIC)

    def _clic(self, indice):
        antes = self._texto()
        self.salida_bloqueada = None
        self.page.locator("main a").nth(indice).click()
        self._esperar(antes)
        return self.salida_bloqueada

    def _enlaces(self):
        return [
            e
            for e in self.page.evaluate(JS_ENLACES)
            if e["texto"]
            and not ENCABEZADO.match(e["texto"])
            and not re.match(r"^https?://(www\.)?gore|^http://www\.", e["texto"], re.I)
        ]

    @staticmethod
    def _clave(e):
        return (e["texto"], e["onclick"][:200], e["href"])

    def _abrir_ficha(self, codigo):
        self.page.goto(self.url_base.format(codigo=codigo), wait_until="domcontentloaded", timeout=60000)
        self.page.wait_for_selector("main a", state="attached", timeout=60000)
        self.page.wait_for_function(
            "() => /01\\. Actos y documentos|Transparencia Activa/.test(document.body.innerText)", timeout=60000
        )
        time.sleep(PAUSA_CLIC)
        # imágenes presentes en la portada de la ficha (logos, banners): no cuentan como contenido publicado
        self.img_base = self.page.evaluate("() => [...document.images].map(i => i.src)")

    def _enlace_externo(self, url, ruta, n=1):
        codigo_http = "" if "/PortalPdT/documents/" in url else estado_http(self.http, url)
        tipo = "archivo alojado en el Portal" if "/PortalPdT/documents/" in url else "enlace externo"
        ok = codigo_http == "" or (isinstance(codigo_http, int) and codigo_http < 400)
        return {
            "estado": "EX" if ok else "ER",
            "evidencia": f"{n} {tipo}; primero: {url[:200]}" + (f" (HTTP {codigo_http})" if codigo_http != "" else ""),
            "ruta": ruta,
        }

    # ---------- recorrido de un ítem ----------
    def item(self, codigo, patron):
        """Abre la ficha del GORE y entra al ítem cuyo nombre coincide con el patrón."""
        self._abrir_ficha(codigo)
        enlaces = self._enlaces()
        inicio = next((e for e in enlaces if re.search(patron, e["texto"], re.I)), None)
        if inicio is None:
            return {"estado": "ER", "evidencia": "ítem no encontrado en la portada de Transparencia Activa", "ruta": ""}
        nombre = inicio["texto"]
        if "(*)" in nombre:
            return {"estado": "SD", "evidencia": "ítem marcado (*) «no publica información»", "ruta": nombre}
        if es_archivo_o_externo(inicio["href"], self.host):
            return self._enlace_externo(inicio["href"], nombre)
        if "PrimeFaces.ab" not in inicio["onclick"]:
            return {"estado": "EX", "evidencia": f"enlace directo: {inicio['href'][:200]}", "ruta": nombre}

        antes = {self._clave(e) for e in enlaces}
        salida = self._clic(inicio["i"])
        if salida:
            return self._enlace_externo(salida, nombre)
        ruta, pila, candidato, mensajes, clics = [nombre], [], None, [], 1
        while clics < MAX_CLICS:
            cont = self.page.evaluate(JS_CONTENIDO, self.img_base)
            if cont:
                ev = (
                    f"{cont['filas']} filas × {cont['columnas']} col."
                    if cont["tipo"] == "tabla"
                    else f"imagen incrustada en el Portal ({cont['n']}): {cont.get('src', '')}"
                )
                return {"estado": "OK", "evidencia": ev, "ruta": " > ".join(ruta)}
            ahora_enl = self._enlaces()
            nuevos = [e for e in ahora_enl if self._clave(e) not in antes and not re.match(r"^\d\d\. ", e["texto"])]
            externos = [e for e in nuevos if es_archivo_o_externo(e["href"], self.host)]
            navegables = [
                e
                for e in nuevos
                if not es_archivo_o_externo(e["href"], self.host)
                and "PrimeFaces.ab" in e["onclick"]
                and "scrollElemento" not in e["onclick"]
                and e["texto"] not in ruta
            ]
            navegables.sort(key=lambda e: -puntaje_periodo(e["texto"]))
            if externos and candidato is None:
                candidato = self._enlace_externo(externos[0]["href"], " > ".join(ruta), len(externos))
            if navegables:
                pila.append([e["texto"] for e in navegables[1 : 1 + HERMANOS]])
                antes = {self._clave(e) for e in ahora_enl}
                ruta.append(navegables[0]["texto"])
                salida = self._clic(navegables[0]["i"])
                clics += 1
                if salida:
                    return candidato or self._enlace_externo(salida, " > ".join(ruta))
                continue
            m = MENSAJE_VACIO.search(self._texto())
            if m:
                mensajes.append(m.group(0))
            # callejón sin salida: probar un período o subcarpeta hermana
            movido = False
            while pila:
                if pila[-1]:
                    txt = pila[-1].pop(0)
                    e = next((x for x in self._enlaces() if x["texto"] == txt), None)
                    if e:
                        ruta[-1] = txt
                        antes = {self._clave(x) for x in self._enlaces()}
                        salida = self._clic(e["i"])
                        clics += 1
                        if salida:
                            return candidato or self._enlace_externo(salida, " > ".join(ruta))
                        movido = True
                        break
                else:
                    pila.pop()
                    ruta.pop()
            if not movido:
                break
        if candidato:
            return candidato
        return {
            "estado": "SD",
            "evidencia": "sin registros en el período más reciente ni en hasta 3 períodos anteriores"
            + (" · " + "; ".join(dict.fromkeys(mensajes)) if mensajes else ""),
            "ruta": " > ".join(ruta),
        }

    def categoria(self, codigo, cat):
        """Estado de una categoría (OK, EX, SD o ER) y su detalle, probando cada nombre posible del ítem."""
        mejor, intentos = None, 0
        for patron in CATEGORIAS[cat][1]:
            intentos += 1
            try:
                r = self.item(codigo, patron)
            except Exception as e:  # una falla del instrumento no debe detener el recorrido completo
                r = {
                    "estado": "ER",
                    "evidencia": f"falla del recorrido: {type(e).__name__}: {str(e)[:150]}",
                    "ruta": "",
                }
                self.log.warning("%s %s: %s", codigo, cat, r["evidencia"])
            if mejor is None or RANGO[r["estado"]] > RANGO[mejor["estado"]]:
                mejor = r
            if r["estado"] == "OK":
                break
        mejor["intentos"] = intentos
        return mejor


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gore", nargs="*", help="códigos o nombres de GORE (por defecto, los 16)")
    ap.add_argument("--categorias", nargs="*", default=list(CATEGORIAS), help="categorías A…M")
    ap.add_argument("--capturas", action="store_true", help="guarda una captura PNG de cada celda")
    ap.add_argument("--visible", action="store_true", help="muestra el navegador mientras recorre")
    ap.add_argument("--url-base", default=URL_FICHA, help="plantilla de URL (para pruebas)")
    ap.add_argument("--etiqueta", default=hoy(), help="sufijo de los archivos de salida")
    ap.add_argument(
        "--ignorar-robots", action="store_true", help="no consultar robots.txt (justifíquelo en el informe)"
    )
    a = ap.parse_args()
    configurar_robots(a.ignorar_robots)

    log = logger("portal")
    prueba = a.url_base.format(codigo="AB075") if "{codigo}" in a.url_base else a.url_base
    if prueba.startswith("http") and not robots_permite(prueba):
        raise SystemExit(
            "robots.txt del Portal no permite este recorrido. Revise la política del sitio; "
            "si decide continuar, use --ignorar-robots y declárelo en el informe de la ronda."
        )
    gores = cargar_gores(a.gore)
    jsonl = SALIDAS / f"portal_celdas_{a.etiqueta}.jsonl"
    hechas = {(r["codigo"], r["categoria"]) for r in leer_jsonl(jsonl)}  # permite retomar un recorrido cortado
    http = sesion()
    with sync_playwright() as p:
        nav = p.chromium.launch(headless=not a.visible)
        ctx = nav.new_context(
            user_agent=USER_AGENT, locale="es-CL", accept_downloads=True, viewport={"width": 1280, "height": 900}
        )
        page = ctx.new_page()
        rec = Recorrido(page, http, log, a.url_base)
        for g in gores:
            for cat in a.categorias:
                if (g["codigo"], cat) in hechas:
                    continue
                t0 = time.time()
                r = rec.categoria(g["codigo"], cat)
                reg = {
                    "codigo": g["codigo"],
                    "gore": g["gore"],
                    "categoria": cat,
                    "nombre_categoria": CATEGORIAS[cat][0],
                    **r,
                    "fecha_hora_utc": ahora(),
                    "segundos": round(time.time() - t0, 1),
                }
                if a.capturas:
                    img = SALIDAS / "capturas" / f"{g['codigo']}_{cat}.png"
                    img.parent.mkdir(exist_ok=True)
                    page.screenshot(path=str(img), full_page=True)
                    reg["captura"] = str(img.name)
                guardar_jsonl(reg, jsonl)
                log.info("%s %-3s %s  %s", g["gore"], cat, reg["estado"], reg["evidencia"][:90])
        nav.close()

    celdas = leer_jsonl(jsonl)
    guardar_csv(celdas, SALIDAS / f"portal_detalle_{a.etiqueta}.csv")
    matriz = {}
    for c in celdas:
        matriz.setdefault(c["gore"], {"gore": c["gore"]})[c["categoria"]] = c["estado"]
    for f in matriz.values():
        vals = [f.get(k) for k in CATEGORIAS if f.get(k)]
        f["indice"] = round(sum(v in ("OK", "EX") for v in vals) / len(vals) * 100, 1) if vals else ""
    guardar_csv(list(matriz.values()), SALIDAS / f"portal_matriz_{a.etiqueta}.csv", ["gore", *CATEGORIAS, "indice"])
    log.info("Listo: %d celdas. Matriz en %s", len(celdas), SALIDAS / f"portal_matriz_{a.etiqueta}.csv")


if __name__ == "__main__":
    main()
