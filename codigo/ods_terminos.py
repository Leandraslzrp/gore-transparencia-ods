"""
Reglas de detección de términos ODS (sección 2 del protocolo) y de los 17 ODS por número y nombre.

Términos núcleo (generan menciones codificables):
  ODS                                  palabra completa en MAYÚSCULAS (evita «métodos», «todos»); no cuenta
                                       encabezados en minúsculas/versalitas ni URL
  Objetivo(s) de Desarrollo Sostenible singular/plural, «de/del», «sostenible/sustentable», sin distinguir mayúsculas
  Agenda 2030                          sin distinguir mayúsculas
  ODS 16                               «ODS 16», «ODS16», «ODS N.° 16»
Términos de contexto (se cuentan, no se codifican): desarrollo sostenible, sostenibilidad, Naciones Unidas.
"""

import re
import unicodedata

NUCLEO = {
    "ODS": re.compile(r"(?<![\w/.-])ODS(?![\w/-])"),
    "Objetivos de Desarrollo Sostenible": re.compile(
        r"\bobjetivos?\s+del?\s+desarrollo\s+sost[ea]nibles?\b"
        r"|\bobjetivos?\s+del?\s+desarrollo\s+sustentables?\b",
        re.I,
    ),
    "Agenda 2030": re.compile(r"\bagenda\s+2030\b", re.I),
    "ODS 16": re.compile(r"(?<![\w/.-])ODS\s*(?:N\.?\s*[°º]?\s*)?16\b"),
}
CONTEXTO = {
    "desarrollo sostenible": re.compile(r"\bdesarrollo\s+sost[ea]nible\b", re.I),
    "sostenibilidad": re.compile(r"\bsostenibilidad\b", re.I),
    "Naciones Unidas": re.compile(r"\bnaciones\s+unidas\b", re.I),
}
# Nombres oficiales abreviados de los 17 ODS (sin tildes; se compara sobre texto normalizado)
NOMBRES_ODS = {
    1: r"fin de la pobreza",
    2: r"hambre cero",
    3: r"salud y bienestar",
    4: r"educacion de calidad",
    5: r"igualdad de genero",
    6: r"agua limpia",
    7: r"energia asequible",
    8: r"trabajo decente",
    9: r"industria,? innovacion e infraestructura",
    10: r"reduccion de las desigualdades",
    11: r"ciudades y comunidades sostenibles",
    12: r"produccion y consumo responsables?",
    13: r"accion por el clima",
    14: r"vida submarina",
    15: r"vida de ecosistemas terrestres",
    16: r"paz,? justicia e instituciones solidas",
    17: r"alianzas para lograr los objetivos",
}
NUMERO_ODS = re.compile(r"(?<![\w/.-])(?:ODS|SDG)\s*(?:N\.?\s*[°º]?\s*|#)?0?(\d{1,2})\b")
NUMERO_EN_TABLA = re.compile(
    r"(?<![\d.])(\d{1,2})\.\s+(Fin|Hambre|Salud|Educaci|Igualdad|Agua|Energ|Trabajo|Industria|"
    r"Reducci|Ciudades|Producci|Acci|Vida|Paz|Alianzas)"
)  # p. ej. «16. Paz, justicia…»
NUMERO_NOMBRE_LARGO = re.compile(
    r"\bobjetivos?\s+del?\s+desarrollo\s+sost[ea]nibles?\s*(?:N\.?\s*[°º]?\s*)?(\d{1,2})\b", re.I
)
META = re.compile(r"\bmetas?\s+(\d{1,2})\.(\d{1,2}|[a-c])\b", re.I)


def sin_tildes(t):
    """Texto en minúsculas y sin tildes, para comparar nombres."""
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn").lower()


def normalizar(texto):
    """Une palabras cortadas por guion al final de línea y colapsa espacios (típico en PDF)."""
    texto = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", texto)
    return re.sub(r"\s+", " ", texto)


def contar(texto, contexto=True):
    """Cuenta coincidencias por término. Devuelve dict término → n."""
    t = normalizar(texto)
    out = {k: len(rx.findall(t)) for k, rx in NUCLEO.items()}
    if contexto:
        out.update({k: len(rx.findall(t)) for k, rx in CONTEXTO.items()})
    return out


def tiene_nucleo(texto):
    """True si el texto contiene al menos un término núcleo de los ODS."""
    t = normalizar(texto)
    return any(rx.search(t) for rx in NUCLEO.values())


def fragmentos(texto, ancho=220, maximo=5):
    """Extractos alrededor de cada término núcleo (para que la persona codificadora lea el contexto)."""
    t = normalizar(texto)
    out = []
    for k, rx in NUCLEO.items():
        for m in rx.finditer(t):
            a, b = max(0, m.start() - ancho), min(len(t), m.end() + ancho)
            out.append(f"[{k}] …{t[a:b]}…")
            if len(out) >= maximo:
                return out
    return out


def ods_mencionados(texto):
    """Qué ODS (1–17) se nombran por número («ODS 11», «16. Paz…») o por nombre oficial, y metas citadas."""
    t = normalizar(texto)
    tn = sin_tildes(t)
    nums = {int(n) for n in NUMERO_ODS.findall(t) if 1 <= int(n) <= 17}
    nums |= {int(n) for n, _ in NUMERO_EN_TABLA.findall(t) if 1 <= int(n) <= 17}
    nums |= {int(n) for n in NUMERO_NOMBRE_LARGO.findall(t) if 1 <= int(n) <= 17}
    nombres = {n for n, rx in NOMBRES_ODS.items() if re.search(rx, tn)}
    metas = sorted({f"{a}.{b}" for a, b in META.findall(t) if 1 <= int(a) <= 17})
    return {"por_numero": sorted(nums), "por_nombre": sorted(nombres), "todos": sorted(nums | nombres), "metas": metas}


if __name__ == "__main__":  # pruebas rápidas
    ej = (
        "La ERD se alinea con los Objetivos de Desarrollo Sostenible (ODS) de la Agenda 2030. "
        "El eje 4 contribuye al ODS 16 y al Objetivo de Desarrollo Sostenible 11. Métodos y todos no cuentan. "
        "ods minúscula no cuenta. Tabla: 16. Paz, justicia e instituciones sólidas; meta 16.6."
    )
    print(contar(ej))
    print(ods_mencionados(ej))
    print(fragmentos(ej, 40))
