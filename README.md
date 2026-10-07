# Transparencia activa y ODS en los Gobiernos Regionales de Chile

Código abierto para medir, de forma reproducible, la transparencia activa de los 16 Gobiernos Regionales (GORE) de Chile y cómo divulgan los Objetivos de Desarrollo Sostenible (ODS). Acompaña el paper *¿Transparencia nominal o efectiva? Divulgación de los ODS y trazabilidad del gasto en los Gobiernos Regionales de Chile* (Salazar Pincheira, Morales Parada y Hollander Sanhueza, 2026).

El código cubre cuatro mediciones y un visor, organizados en **rondas de medición** que cualquier persona puede repetir (se propone tres veces al año; ver [`documentacion/PROTOCOLO_RONDAS.md`](documentacion/PROTOCOLO_RONDAS.md)):

| Módulo | Qué mide | Script |
|---|---|---|
| 1. Informes del CPLT | Índices de fiscalización de transparencia activa del Consejo para la Transparencia por año, su evolución y pruebas entre años | `codigo/cplt_informes.py` |
| 2. Scraping del Portal de Transparencia | Estado de las 15 categorías de los artículos 6.° y 7.° de la Ley N.° 20.285 en cada GORE (publicada, externa, sin datos o con error) | `codigo/portal_scraping.py`, `codigo/portal_indice.py` |
| 3. Divulgación de los ODS | Menciones de los ODS en el sitio web, la Estrategia Regional de Desarrollo (ERD) y la cuenta pública de cada GORE, clasificadas como retóricas o sustantivas | `codigo/ods_web.py`, `codigo/ods_documentos.py`, `codigo/ods_codificacion.py`, `codigo/ods_graficos.py` |
| 4. Análisis estadístico | Proporciones con intervalos de Wilson, Friedman, Wilcoxon, Spearman con *bootstrap*, Bland-Altman, κ de Cohen y comparación entre rondas | `codigo/analisis_ronda.py` (`analisis_paper_2026.py` para el paper) |
| Cierre de ronda | Datos en formato estándar, fiabilidad entre codificadores y manifiesto con huellas SHA-256 | `codigo/cerrar_ronda.py` |
| Visor web | Página con la divulgación de los ODS, el índice del CPLT y la disponibilidad en el Portal por GORE, con la evolución de cada medición, lista para GitHub Pages | `codigo/visor.py` → `docs/index.html` |
| Actualización del Portal | Repite solo el recorrido del Portal (automático) entre rondas y actualiza el visor | `codigo/actualizar_portal.py` |

## Instalación

```bash
python3 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt               # versiones exactas; si falla: requirements-min.txt
python -m playwright install chromium                   # navegador para el Portal de Transparencia
```

Para leer PDF escaneados (OCR) instale además Tesseract con español y Poppler (macOS: `brew install tesseract tesseract-lang poppler`; Ubuntu: `sudo apt install tesseract-ocr tesseract-ocr-spa poppler-utils`).

**Antes de recolectar**, escriba su correo en `config/contacto.txt` (una sola línea; hay un ejemplo en `config/contacto.txt.ejemplo`). Los sitios lo ven en cada visita. Ese archivo no se sube a GitHub.

Compruebe la instalación con las pruebas (no necesitan internet): `python ejecutar_todo.py pruebas`.

## Uso rápido: una ronda de medición

```bash
python ejecutar_todo.py recolectar --etiqueta 2027-04-10     # automático: CPLT, Portal, ODS y planilla de revisión manual
#   → una persona revisa salidas/revision_manual_2027-04-10.xlsx (documentacion/PROTOCOLO_REVISION_MANUAL.md)
python ejecutar_todo.py plantilla --etiqueta 2027-04-10      # valida la revisión y genera la planilla de codificación
#   → dos personas codifican salidas/codificacion_ods_2027-04-10.xlsx
python ejecutar_todo.py cerrar 2027-1 --etiqueta 2027-04-10 \
       --fecha-scraping "10 de abril de 2027" --fecha-ods "12 al 20 de abril de 2027"
#   → mediciones/2027-1/ (datos), resultados/2027-1/ (análisis y figuras), docs/index.html (visor)
python ejecutar_todo.py verificar 2027-1                     # comprueba que los datos no cambiaron después del cierre
```

Entre la recolección y la codificación se hace una revisión manual de lo que el código no pudo encontrar ([`documentacion/PROTOCOLO_REVISION_MANUAL.md`](documentacion/PROTOCOLO_REVISION_MANUAL.md)). El paso a paso completo, con la lista de verificación, está en [`documentacion/PROTOCOLO_RONDAS.md`](documentacion/PROTOCOLO_RONDAS.md); el contenido de cada archivo, en [`documentacion/DICCIONARIO_DATOS.md`](documentacion/DICCIONARIO_DATOS.md).

Cada script acepta `--help` y la mayoría `--gore AB098 AB081` para trabajar con algunos GORE.

### 1. Informes del CPLT

El CPLT publica sus resultados como informes y planillas, no como datos abiertos. Los índices de cada año se guardan en `datos/referencia_cplt.csv` (columnas `codigo`, `gore`, `cplt_2024`, `cplt_2025`, `cplt_2026`…) y la fuente de cada año en `config/cplt_informes.csv`.

```bash
python codigo/cplt_informes.py resumen                 # valida los datos y compara años → salidas/cplt_*.csv
python codigo/cplt_informes.py agregar 2027 nuevo.csv  # suma un año (CSV con columnas codigo o gore, e indice)
python codigo/cplt_informes.py descargar               # guarda los informes listados en config/cplt_informes.csv
```

### 2. Scraping del Portal de Transparencia

```bash
python codigo/portal_scraping.py --etiqueta 2026-10-06
python codigo/portal_indice.py salidas/portal_matriz_2026-10-06.csv                     # índice y sensibilidad
python codigo/portal_indice.py datos/referencia_scraping_2026-07-22.csv salidas/portal_matriz_2026-10-06.csv   # compara dos recorridos
```

Reglas de puntaje: **OK** (tabla con registros) y **EX** (enlace externo operativo) valen 1; **SD** (sin datos) y **ER** (error o ítem inexistente) valen 0. El índice es el porcentaje de las 15 categorías con valor 1. Solo se guarda el tamaño de cada tabla, nunca su contenido, porque incluye datos personales.

### 3. Divulgación de los ODS

```bash
python codigo/ods_web.py --etiqueta 2026-10-06                 # buscadores de los sitios; abre cada resultado y verifica el término
python codigo/ods_web.py --gore AB077 AB079 --completo         # recorre el mapa del sitio cuando el buscador no sirve
python codigo/ods_documentos.py --etiqueta 2026-10-06          # descarga ERD y cuentas públicas y marca los términos página a página
python codigo/ods_codificacion.py plantilla --web salidas/ods_menciones_web_FECHA.csv --docs salidas/ods_pasajes_FECHA.csv \
       --documentos salidas/ods_documentos_FECHA.csv --busquedas salidas/ods_busquedas_FECHA.csv
python codigo/ods_codificacion.py kappa salidas/codificacion_ods_FECHA.xlsx   # después de codificar a mano
```

- **Términos**: «ODS» (en mayúsculas y como palabra completa), «Objetivo(s) de Desarrollo Sostenible», «Agenda 2030» y «ODS 16».
- **Retórica**: menciona los ODS sin vincularlos con objetivos, metas, indicadores o presupuesto del GORE. **Sustantiva**: los vincula. Ante la duda, retórica.
- **Nivel de la ERD**: 0 sin mención, 1 declarativa, 2 vinculación (parcial o estratégica), 3 operacionalizada (ODS asignados a indicadores o presupuesto).
- **Mapa de la ERD**: cada ODS se codifica 2 (vinculado), 1 (solo contexto) o 0 (no se nombra).
- **Robots.txt**: antes de cada descarga se consulta el `robots.txt` del sitio; las páginas prohibidas no se visitan y quedan en `salidas/robots_bloqueadas_FECHA.csv`.
- **Huellas**: cada PDF y cada página con mención quedan con su huella SHA-256, para saber exactamente qué versión se analizó.
- La clasificación la hacen personas. El código encuentra y verifica las menciones; la columna «Sugerencia automática» es solo una ayuda.
- Los documentos que los sitios bloquean se dejan en `documentos_manuales/` como `{codigo}_erd.pdf` o `{codigo}_cuenta_publica.pdf`, y el código los lee igual. En `config/gores.csv`, una cuenta pública que existe solo en video se marca empezando la URL con `video:`.

### 4. Cierre, análisis y visor

```bash
python codigo/cerrar_ronda.py 2027-1 --codificacion salidas/codificacion_ods_2027-04-10.xlsx --etiqueta 2027-04-10
python codigo/analisis_ronda.py 2027-1          # → resultados/2027-1/analisis_2027-1.xlsx (compara con la ronda anterior)
python codigo/ods_graficos.py --ronda 2027-1    # → resultados/2027-1/figuras/ y resultados/evolucion_rondas.png
python codigo/visor.py --ronda 2027-1           # → docs/index.html
```

Los tres últimos pasos se hacen juntos con `python ejecutar_todo.py analizar 2027-1` (y `cerrar` los incluye).

El visor se genera completo desde la ronda, sin pasos manuales. Para publicarlo: en GitHub, *Settings → Pages → Deploy from a branch → main / docs* (ver [`documentacion/PUBLICAR.md`](documentacion/PUBLICAR.md)).

## Mantener el visor al día

El visor muestra siempre **la medición más reciente del Portal** y su evolución; los resultados de los ODS son los de la **última ronda cerrada**, porque requieren codificación humana.

El recorrido del Portal es automático y se puede repetir cuando se quiera (se sugiere una vez al mes), de dos formas:

- **Desde GitHub, sin computador:** pestaña *Actions* → **Actualizar Portal y visor** → *Run workflow*. Recorre el Portal en los servidores de GitHub, guarda la medición en `actualizaciones/portal/` y publica el visor. Para que corra solo cada mes, quite el `#` de las líneas `schedule` en `.github/workflows/actualizar-portal.yml`.
- **Desde su computador:** `python ejecutar_todo.py actualizar --publicar`.

Cada medición queda en `actualizaciones/portal/registro.csv` con su fecha, método y huella SHA-256. El visor indica el método de cada medición, porque los recorridos del equipo (julio y septiembre de 2026) y los del código pueden diferir por método.

## Estructura

```
ejecutar_todo.py        punto de entrada: recolectar, plantilla, cerrar, analizar, actualizar, visor, paper, pruebas
codigo/                 los módulos (un archivo por tarea) y la plantilla del visor
config/                 gores.csv (sitios, buscadores, URL de ERD y cuentas públicas) · cplt_informes.csv · contacto.txt
datos/                  índices del CPLT (referencia_cplt.csv) y recorridos del Portal de julio y septiembre de 2026
mediciones/<ronda>/     datos de cada ronda en formato estándar + manifiesto.json (no se editan)
actualizaciones/portal/ mediciones del Portal entre rondas (registro.csv + una matriz por fecha)
resultados/<ronda>/     análisis y figuras de cada ronda · serie_rondas.csv (todas las rondas)
docs/index.html         visor generado (GitHub Pages)
documentos_manuales/    PDF aportados a mano cuando el sitio bloquea la descarga
paper_2026/             análisis del paper (congelado), su planilla de codificación y las salidas del código del 29-09-2026
documentacion/          protocolo de rondas, protocolo de revisión manual, diccionario de datos y guía de publicación
tests/                  pruebas automáticas (sin internet)
salidas/                resultados crudos de cada recolección (no se versionan)
```

El estilo del código se revisa con [ruff](https://docs.astral.sh/ruff/) (`ruff check .` y `ruff format .`; configuración en `pyproject.toml`).

## Verificar las cifras del paper sin internet

```bash
python ejecutar_todo.py pruebas          # comprueba la integridad de la ronda 2026-1 y sus cifras
python ejecutar_todo.py analizar 2026-1  # el análisis completo de la ronda del paper
python ejecutar_todo.py paper            # el análisis original del paper, con los tres recorridos del Portal
```

Cifras esperadas: CPLT 76,6 / 76,1 / 92,3 % (2024–2026; Friedman p = 0,001; W = 0,42); scraping de julio 86,7 %; scraping vs. CPLT 2026 ρ = −0,03 (IC 95 % −0,47 a 0,45); 13 de 16 GORE mencionan los ODS en su sitio web; 7 de 16 ERD con vínculo sustantivo; 0 de 14 cuentas públicas (IC 95 % 0–22 %; corregido el 07-10-2026: se agregó la de La Araucanía); κ = 0,87 (n = 48).

## Transparencia y reproducibilidad

- **Datos y código abiertos** con licencias MIT y CC BY 4.0; archivo permanente en Zenodo con DOI (ver `documentacion/PUBLICAR.md`).
- **Versiones exactas** de las librerías (`requirements.txt`) y registro del entorno real en el manifiesto de cada ronda.
- **Integridad**: huella SHA-256 de cada archivo de la ronda, de cada PDF analizado y del texto de cada página web con mención.
- **Fiabilidad**: dos codificadores independientes y κ de Cohen en menciones, documentos y mapa ERD × ODS.
- **Ética de la recolección**: solo información pública, *user-agent* identificado con correo, pausas entre solicitudes y respeto de `robots.txt`; no se guardan datos personales.
- **Pruebas automáticas** que verifican en cada cambio que la ronda del paper se sigue reproduciendo.

## Limitaciones

- Los sitios cambian: revise `config/gores.csv` antes de cada medición y las celdas con estado ER.
- Si el Portal cambia los nombres de sus ítems, ajuste `CATEGORIAS` en `codigo/portal_scraping.py`.
- El CPLT y el scraping miden aspectos distintos; compárelos como instrumentos, no como una misma serie.

## Licencia y cita

Código bajo licencia MIT (`LICENSE`); datos y resultados bajo CC BY 4.0 (`LICENSE-datos`). Para citar, ver `CITATION.cff`.
