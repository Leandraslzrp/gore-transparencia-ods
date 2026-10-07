# Registro de cambios

Formato: versiones del código (ver `PUBLICAR.md`) y rondas de medición. Cada ronda anota fechas, responsables y cambios en `config/gores.csv`.

## [1.4.0] — 2026-10-07

Limpieza del repositorio. No cambia ningún resultado: las 23 pruebas pasan y el visor, el análisis de la ronda 2026-1 y el análisis del paper son idénticos a los de la versión 1.3.0.

### Cambiado
- **Carpetas ordenadas.** Los módulos pasan a `codigo/`; el paper 2026 (análisis, conversión, planilla y salidas del 29-09) a `paper_2026/`; los archivos de referencia del CPLT y de los recorridos de 2026 a `datos/`; los protocolos, el diccionario de datos y la guía de publicación a `documentacion/`. En la raíz queda `ejecutar_todo.py` como único punto de entrada.
- `ejecutar_todo.py`: nuevos comandos `analizar`, `visor` y `paper`; funciona desde cualquier carpeta.
- El análisis del paper lee por defecto `paper_2026/resultados/` y reproduce las cifras sin copiar archivos (`python ejecutar_todo.py paper`).
- Código con formato uniforme (ruff, `pyproject.toml`) y una línea que explica cada función; GitHub Actions revisa el estilo en cada cambio.
- `portal_indice.py --cplt` acepta `datos/referencia_cplt.csv`.

### Eliminado
- Funciones repetidas (κ de Cohen e índice del Portal tenían tres copias; ahora están solo en `codigo/ronda.py`), importaciones y funciones sin uso.

### Corregido
- `resultados/2026-1/` y `resultados/serie_rondas.csv` se regeneraron con la corrección de La Araucanía (0 de 14 cuentas públicas).

## [1.3.0] — 2026-10-07

### Agregado
- `PROTOCOLO_REVISION_MANUAL.md` y `revision_manual.py`: revisión manual sistemática entre la recolección y la codificación. Genera la lista de casos pendientes (celdas ER/SD del Portal, documentos no disponibles o escaneados, sitios sin menciones, páginas bloqueadas por robots.txt y una muestra de control de documentos «Sin mención»), registra cada búsqueda y mención halladas a mano y valida que los «No disponible» tengan dos revisores.
- `ejecutar_todo.py plantilla`: exporta la revisión manual y genera la planilla de codificación con las menciones manuales (`M001`…).
- `ods_codificacion.py plantilla --manual`.
- Los archivos de la revisión manual quedan en `mediciones/<ronda>/crudos/` con huella SHA-256.

### Ronda 2026-1 (corregida el 7 de octubre de 2026)
- Cuenta pública 2025 de La Araucanía: de «No disponible» a **«Sin mención»**. Estaba publicada como documento en un visor embebido (Heyzine) en https://gorearaucania.cl/cuentas-publicas, no solo en video. PDF original obtenido desde el visor (`documentos_manuales/AB085_cuenta_publica.pdf`; 70 páginas; SHA-256 `b9716f53…`): 0 términos ODS núcleo; 4 «desarrollo sostenible» y 3 «sostenibilidad» (contexto).
- Cuentas públicas disponibles: **14** (antes 13); con vínculo sustantivo: 0 de 14 (IC de Wilson 0–22 %).
- Archivos corregidos: `ods_documentos.csv`, `ods_resumen_gore.csv` y `config_gores.csv` de la ronda; `config/gores.csv` (URL de la cuenta pública de AB085); `datos/planilla_codificacion_ods.xlsx` (hoja `Cambios_2026-10-07`, con el valor anterior de cada celda en un comentario). El manifiesto registra las nuevas huellas en `correcciones`.
- Lección incorporada al protocolo: revisar los visores embebidos (paso 4 de la sección 2 de `PROTOCOLO_REVISION_MANUAL.md`).

## [1.2.0] — 2026-10-06

### Agregado
- Mediciones del Portal entre rondas (`actualizaciones/portal/`, `historial_portal.py`, `actualizar_portal.py`) con registro de fecha, método y huella SHA-256. Se incorporan los tres recorridos de 2026: 22 de julio y 25 de septiembre (equipo) y 29 de septiembre (código).
- Visor: la divulgación de los ODS es la primera pestaña y se separa por fuente (resumen, ERD con mapa de 17 ODS y extractos, sitios web con cada página y su justificación, cuentas públicas), con gráfico de los ODS más vinculados y leyenda de colores de los 17 ODS; el índice del CPLT y la disponibilidad en el Portal (scraping) van en pestañas separadas; selector de medición del Portal, columna de cambio y evolución por GORE.
- GitHub Actions: **Actualizar Portal y visor** (manual; mensual opcional).
- `ejecutar_todo.py actualizar`.

### Cambiado
- El visor muestra la medición más reciente del Portal (antes, la de la ronda) y textos de notas generados desde los datos.
- `cerrar_ronda.py` agrega la matriz del Portal de la ronda al historial.

## [1.1.0] — 2026-10-06

Rondas de medición reproducibles para repetir el estudio tres veces al año.

### Agregado
- Formato estándar de ronda en `mediciones/<ronda>/` con manifiesto SHA-256 y versiones del software (`ronda.py`, `cerrar_ronda.py`).
- `analisis_ronda.py`: análisis de cualquier ronda, comparación con la anterior y serie histórica (`resultados/serie_rondas.csv`).
- Plantilla de codificación con hoja `Documentos` (dos codificadores) y filas cod. 1 / cod. 2 / consenso con nivel en `Mapa_17_ODS`; κ de documentos y del mapa.
- Control de `robots.txt` en todas las descargas (`--ignorar-robots` solo con justificación) y registro de las páginas omitidas.
- Huella SHA-256 de cada PDF analizado y del texto de cada página web con mención.
- Correo de contacto en `config/contacto.txt` (ya no se edita el código).
- Pruebas automáticas sin internet (`tests/`) y flujo de GitHub Actions.
- `PROTOCOLO_RONDAS.md`, `DICCIONARIO_DATOS.md`, `PUBLICAR.md`, `.zenodo.json`, `requirements.txt` con versiones exactas y `requirements-min.txt`.
- Gráfico de evolución entre rondas.

### Cambiado
- El visor y los gráficos leen una ronda cerrada; ya no dependen de archivos preparados a mano (`datos/ods_resumen_gore.csv` y `datos/erd_mapa_ods.csv` se eliminaron: ahora los genera `cerrar_ronda.py`).
- `ejecutar_todo.py` organiza el trabajo en `recolectar`, `cerrar`, `verificar` y `pruebas`.
- `analisis_estadistico_excel.py` pasa a llamarse `analisis_paper_2026.py` y queda congelado.

### Ronda 2026-1 (paper)
- Creada desde la planilla consolidada del paper con `herramientas/convertir_planilla_2026.py`. Portal: 22 y 27 de julio de 2026; ODS: 23 al 29 de septiembre de 2026.
- Reproduce las cifras publicadas: índice 86,7 %; ρ = −0,03 con CPLT 2026; 13/16 GORE con mención web; 7/16 ERD con vínculo sustantivo; 0/13 cuentas públicas; κ = 0,87 (n = 48).
- En esta ronda el mapa ERD × ODS y la clasificación de documentos tienen una sola codificación registrada (la segunda codificación se hizo sobre conteos y menciones). Desde la ronda 2026-2 el protocolo exige dos codificadores también en esas hojas.

## [1.0.0] — 2026-10-01

Primera versión: informes del CPLT, scraping del Portal, búsqueda de ODS en sitios, ERD y cuentas públicas, análisis del paper y visor.
