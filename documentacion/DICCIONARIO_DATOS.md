# Diccionario de datos

Cada ronda vive en `mediciones/<ronda>/` con estos archivos (CSV en UTF-8, separados por comas). Los genera `codigo/cerrar_ronda.py`; no se editan a mano.

## portal_matriz.csv — Portal de Transparencia (una fila por GORE)

| Columna | Descripción |
|---|---|
| `codigo` | Código del organismo en el Portal (AB075 … AB098) |
| `gore` | Nombre del Gobierno Regional |
| `A` … `M` | Estado de cada categoría de transparencia activa (art. 6.° y 7.° de la Ley N.° 20.285): **OK** tabla con registros · **EX** enlace externo operativo · **SD** sin datos o «no publica» · **ER** error o ítem inexistente |
| `indice` | % de las 15 categorías con OK o EX |

Categorías: A estructura orgánica · B facultades · C marco normativo · D1 planta · D2 contrata · D3 honorarios · E compras · F transferencias · G actos con efectos sobre terceros · H trámites · I subsidios · J participación ciudadana · K presupuesto · L auditorías · M vínculos institucionales.

## ods_menciones.csv — menciones de los ODS (una fila por página web o página de documento)

| Columna | Descripción |
|---|---|
| `id` | W… (sitio web) o D… (pasaje de documento) |
| `codigo`, `gore` | GORE |
| `fuente` | Sitio web · ERD · Cuenta pública |
| `fecha_o_pagina` | Fecha de la noticia o página del documento |
| `titulo_o_documento`, `url` | Título y URL de la página (o identificador del pasaje) |
| `terminos` | Términos encontrados (ODS, Objetivos de Desarrollo Sostenible, Agenda 2030, ODS 16) |
| `sha256_texto` | Huella del texto leído: permite saber si la página cambió desde la ronda |
| `cod1`, `cod2` | Clasificación de cada codificador: **Retórica** (menciona sin vincular) o **Sustantiva** (vincula con objetivos, metas, indicadores o presupuesto) |
| `consenso` | Clasificación final |
| `justificacion` | Nota del codificador 1 |

## ods_documentos.csv — ERD y cuentas públicas (una fila por documento)

| Columna | Descripción |
|---|---|
| `codigo`, `gore`, `fuente` | GORE y tipo de documento (ERD o Cuenta pública) |
| `documento` | Archivo u origen |
| `sha256` | Huella del PDF leído (comprueba que se analizó exactamente ese archivo) |
| `n_<término>` | Número de apariciones de cada término |
| `cod1`, `cod2`, `consenso` | Sustantiva · Retórica · Sin mención · No disponible |

## erd_mapa_ods.csv — mapa ERD × 17 ODS (consenso; una fila por GORE)

| Columna | Descripción |
|---|---|
| `documento` | ERD codificada |
| `nivel` | Integración de los ODS en la ERD: 0 sin mención · 1 declarativa · 2 vinculación (parcial o estratégica) · 3 operacionalizada |
| `ods_1` … `ods_17` | 2 vinculado a eje, objetivo o indicador · 1 solo contexto · 0 no se nombra |

`erd_mapa_ods_codificadores.csv` tiene la codificación independiente en formato largo (`codigo`, `gore`, `ods`, `cod1`, `cod2`).

## ods_resumen_gore.csv — resumen por GORE

`web_retoricas`, `web_sustantivas` (n.º de menciones web) · `cuenta_publica`, `erd_clasificacion` (mejor clasificación del documento) · `erd_documento` · `erd_nivel`.

## fiabilidad.csv

`medida`, `n`, `acuerdo` (proporción de coincidencias), `kappa` (κ de Cohen). Criterio: κ ≥ 0,60 aceptable; ≥ 0,80 muy bueno.

## manifiesto.json

Nombre de la ronda, fecha de cierre (UTC), fechas de recolección y codificación, versión de Python, sistema y librerías, y la huella SHA-256 y el tamaño de cada archivo de la carpeta.

## Otros archivos de la ronda

`codificacion.xlsx` (planilla codificada original) · `config_gores.csv` (configuración usada) · `crudos/` (salidas sin procesar de los scripts, con fechas y horas de cada consulta).

## Fuera de las rondas

| Archivo | Contenido |
|---|---|
| `datos/referencia_cplt.csv` | Índice de transparencia activa del CPLT por GORE y año (`cplt_2024`, …) |
| `config/gores.csv` | Por GORE: sitio web, tipo de buscador, URL de búsqueda y de listado, URL de la cuenta pública y de la ERD |
| `config/cplt_informes.csv` | Fuente de cada año del CPLT |
| `resultados/serie_rondas.csv` | Indicadores principales de todas las rondas (se crea al analizar) |
| `plantillas/` | Planillas de revisión manual y de codificación en blanco |
| `tests/datos/` | Salidas de ejemplo de la recolección automática (29-09-2026) para las pruebas |
