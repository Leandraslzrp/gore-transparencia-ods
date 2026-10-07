# Medición de la transparencia activa y la divulgación de los ODS en los Gobiernos Regionales de Chile

Código y protocolo para repetir, con el mismo método, la medición del artículo *¿Transparencia nominal o efectiva? Divulgación de los ODS y trazabilidad del gasto en los Gobiernos Regionales de Chile* (Salazar Pincheira, Morales Parada y Hollander Sanhueza, 2026).

Cada medición, llamada **ronda**, cubre los 16 Gobiernos Regionales (GORE) en tres dimensiones: el índice de fiscalización del Consejo para la Transparencia (CPLT), la disponibilidad efectiva de 15 categorías en el Portal de Transparencia y la divulgación de los Objetivos de Desarrollo Sostenible (ODS) en el sitio web, la Estrategia Regional de Desarrollo (ERD) y la cuenta pública de cada GORE. El paso a paso está en el [protocolo de rondas](documentacion/PROTOCOLO_RONDAS.md).

> **Summary in English.** Code and protocol to replicate the measurement used in the paper above. Each measurement round covers Chile's 16 Regional Governments (GORE): the official active-transparency index of the Council for Transparency (CPLT), the actual availability of 15 mandatory categories on the national Transparency Portal (web scraping), and the disclosure of the Sustainable Development Goals (SDGs) on each GORE's website, Regional Development Strategy and annual public account, double-coded as rhetorical or substantive. A manual-review protocol covers what the code cannot find, and every closed round is stored with SHA-256 fingerprints. Documentation is in Spanish.

## Qué incluye

| Etapa | Qué hace | Código |
|---|---|---|
| Índices del CPLT | Reúne los índices de fiscalización por año y los compara | `codigo/cplt_informes.py` |
| Portal de Transparencia | Recorre las 15 categorías de los artículos 6.° y 7.° de la Ley N.° 20.285 en cada GORE y calcula la disponibilidad | `codigo/portal_scraping.py`, `codigo/portal_indice.py` |
| ODS en sitios web y documentos | Busca los términos en los sitios web, la ERD y la cuenta pública, y verifica cada resultado | `codigo/ods_web.py`, `codigo/ods_documentos.py`, `codigo/ods_terminos.py` |
| Revisión manual | Lista lo que el código no pudo encontrar o verificar y registra la búsqueda a mano | `codigo/revision_manual.py` |
| Codificación | Planilla para que dos personas clasifiquen cada mención por separado; acuerdo con κ de Cohen | `codigo/ods_codificacion.py` |
| Cierre y análisis | Datos en formato estándar con huella SHA-256, fiabilidad, intervalos de Wilson, pruebas entre años y comparación con la ronda anterior | `codigo/cerrar_ronda.py`, `codigo/analisis_ronda.py`, `codigo/ods_graficos.py` |

Las planillas que se llenan a mano están en blanco en [`plantillas/`](plantillas/).

## Instalación

Requiere Python 3.12 o superior.

```bash
python3 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt               # versiones exactas; si falla: requirements-min.txt
python -m playwright install chromium                   # navegador para el Portal de Transparencia
```

Para leer PDF escaneados (OCR), instale además Tesseract con español y Poppler (macOS: `brew install tesseract tesseract-lang poppler`; Ubuntu: `sudo apt install tesseract-ocr tesseract-ocr-spa poppler-utils`).

Antes de recolectar, escriba su correo en `config/contacto.txt` (una línea; hay un ejemplo en `config/contacto.txt.ejemplo`). Los sitios lo ven en cada visita, y el archivo no se sube a GitHub.

Compruebe la instalación con las pruebas, que no necesitan internet: `python ejecutar_todo.py pruebas`.

## Una ronda en cuatro comandos

```bash
python ejecutar_todo.py recolectar --etiqueta 2027-06-15     # automático: CPLT, Portal, ODS y planilla de revisión manual
#   → revisión manual de salidas/revision_manual_2027-06-15.xlsx
python ejecutar_todo.py plantilla --etiqueta 2027-06-15      # valida la revisión y genera la planilla de codificación
#   → dos personas codifican salidas/codificacion_ods_2027-06-15.xlsx
python ejecutar_todo.py cerrar 2027-2 --etiqueta 2027-06-15 \
       --fecha-scraping "15 de junio de 2027" --fecha-ods "17 al 25 de junio de 2027"
#   → mediciones/2027-2/ (datos con huella SHA-256) y resultados/2027-2/ (análisis y figuras)
python ejecutar_todo.py verificar 2027-2                     # comprueba que los datos no cambiaron después del cierre
```

Documentación:

- [Protocolo de rondas](documentacion/PROTOCOLO_RONDAS.md): pasos, roles y tiempos.
- [Protocolo de revisión manual](documentacion/PROTOCOLO_REVISION_MANUAL.md): qué revisar a mano y cómo registrarlo.
- [Diccionario de datos](documentacion/DICCIONARIO_DATOS.md): el contenido de cada archivo.
- [Publicar una versión](documentacion/PUBLICAR.md): GitHub y Zenodo.

Cada script de `codigo/` acepta `--help`, y la mayoría acepta `--gore AB098 AB081` para trabajar con algunos GORE.

## Reglas de medición

**Portal de Transparencia.** Cada categoría vale 1 si tiene una tabla con registros (OK) o un enlace externo que responde (EX), y 0 si está sin datos (SD) o con error (ER). El índice de disponibilidad es el porcentaje de las 15 categorías con valor 1. Solo se guarda el tamaño de cada tabla, nunca su contenido, porque puede incluir datos personales.

**Divulgación de los ODS.**

- **Términos:** «ODS» (en mayúsculas y como palabra completa), «Objetivo(s) de Desarrollo Sostenible», «Agenda 2030» y «ODS 16».
- **Retórica:** menciona los ODS sin vincularlos con objetivos, metas, indicadores o presupuesto del GORE. **Sustantiva:** los vincula. Ante la duda, retórica.
- **Nivel de la ERD:** 0 sin mención, 1 declarativa, 2 vinculación, 3 operacionalizada (ODS asignados a indicadores o presupuesto).
- **Mapa de la ERD:** cada ODS se codifica 2 (vinculado), 1 (solo contexto) o 0 (no se nombra).
- La clasificación la hacen personas: el código encuentra y verifica las menciones, y la columna «Sugerencia automática» es solo una ayuda.
- Los documentos que un sitio bloquea se guardan a mano en `documentos_manuales/` como `{codigo}_erd.pdf` o `{codigo}_cuenta_publica.pdf`, y el código los lee igual.

**Recolección responsable.** Solo información pública, identificación con un correo de contacto, pausas de 1 a 2,5 segundos entre solicitudes y respeto de `robots.txt`. Las páginas que un sitio pide no visitar quedan registradas en `salidas/robots_bloqueadas_FECHA.csv`.

## Estructura

```
ejecutar_todo.py        punto de entrada: recolectar, plantilla, cerrar, analizar, verificar, pruebas
codigo/                 un archivo por tarea
config/                 gores.csv (sitios, buscadores y URL de ERD y cuentas públicas) · cplt_informes.csv · contacto.txt
datos/                  referencia_cplt.csv: índices del CPLT por GORE y año
plantillas/             planillas de revisión manual y de codificación, en blanco
documentacion/          protocolos, diccionario de datos y guía de publicación
tests/                  pruebas automáticas y datos de ejemplo
documentos_manuales/    PDF aportados a mano en cada ronda (no se versionan)
salidas/                resultados crudos de cada recolección (no se versionan)
mediciones/, resultados/  datos y análisis de cada ronda cerrada (se crean al cerrar; no se versionan)
```

## Pruebas

`python ejecutar_todo.py pruebas` comprueba que las reglas de búsqueda, el índice, el κ de Cohen y el respeto de `robots.txt` no cambiaron sin querer. También simula dos rondas completas (revisión manual, codificación, cierre, análisis y verificación) con los datos de ejemplo de `tests/datos/`, que son las salidas de la recolección automática del 29 de septiembre de 2026. Las pruebas corren en GitHub en cada cambio, junto con una revisión del estilo del código ([ruff](https://docs.astral.sh/ruff/), configuración en `pyproject.toml`).

## Limitaciones

- Los sitios cambian: revise `config/gores.csv` antes de cada ronda.
- Si el Portal cambia los nombres de sus ítems, ajuste `CATEGORIAS` en `codigo/portal_scraping.py`.
- El CPLT y el Portal miden aspectos distintos; compárelos como instrumentos, no como una misma serie.

## Licencia y cita

Código bajo licencia MIT (`LICENSE`); `config/`, `datos/`, las plantillas y los datos de ejemplo bajo CC BY 4.0 (`LICENSE-datos`). Para citar, ver `CITATION.cff`.
