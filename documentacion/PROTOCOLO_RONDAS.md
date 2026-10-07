# Protocolo de rondas de medición

Este protocolo permite que cualquier persona repita la medición **tres veces al año** con el mismo método y obtenga resultados comparables con el paper de 2026 (ronda `2026-1`). Cada ronda tarda unas **2 a 3 jornadas de trabajo**: medio día de recolección automática, dos días de codificación (dos personas) y una hora para cerrar, analizar y publicar.

## Calendario sugerido

| Ronda | Ventana | Nombre de la carpeta |
|---|---|---|
| 1 | marzo – abril | `AAAA-1` |
| 2 | julio – agosto | `AAAA-2` |
| 3 | noviembre – diciembre | `AAAA-3` |

Reglas del nombre: año, guion y número de ronda (`2027-1`). Así las rondas se ordenan solas y el análisis compara cada una con la anterior. La ronda `2026-1` es la del paper.

Recolecte **todo el Portal en un mismo día** (o en días consecutivos) y anótelo en `--fecha-scraping`. Cuando el CPLT publique un año nuevo, agréguelo antes de analizar (paso 1).

## Entre rondas: el Portal cada mes

El recorrido del Portal no necesita codificación humana, así que puede repetirse cada mes para que el visor esté al día: en GitHub, *Actions* → **Actualizar Portal y visor** → *Run workflow* (o `python ejecutar_todo.py actualizar --publicar`). Revise después las celdas **ER** de la nueva medición en el visor (pestaña *Transparencia activa*, selector «Medición del Portal»).

## Lista de verificación

### 0. Preparación (30 minutos)

- [ ] Descargue la última versión del repositorio (o `git pull`).
- [ ] Instale el entorno: `python -m pip install -r requirements.txt` y `python -m playwright install chromium`.
- [ ] Escriba su correo en `config/contacto.txt` (una línea). Los sitios lo ven en cada visita.
- [ ] Corra las pruebas: `python ejecutar_todo.py pruebas`. Deben terminar en `OK`; si no, no siga y revise el error.

### 1. Actualizar la configuración (1 hora)

- [ ] Abra `config/gores.csv` y compruebe, GORE por GORE, que las URL del sitio, la ERD y la cuenta pública sigan funcionando. Si un GORE publicó una ERD o cuenta pública nueva, reemplace la URL y anótelo en `CHANGELOG.md`.
- [ ] Si el CPLT publicó resultados nuevos: `python codigo/cplt_informes.py agregar AÑO archivo.csv` y registre la fuente en `config/cplt_informes.csv`.
- [ ] No cambie los términos de búsqueda (`codigo/ods_terminos.py`), las categorías del Portal ni las reglas de puntaje. Si es imprescindible, cambie la versión mayor del código (ver `PUBLICAR.md`) y explíquelo, porque la serie deja de ser comparable.

### 2. Recolectar (automático, 2 a 4 horas)

```bash
python ejecutar_todo.py recolectar --etiqueta 2027-04-10
```

- [ ] Revise en `salidas/portal_matriz_2027-04-10.csv` las celdas **ER**; si son fallas del recorrido, repita solo ese GORE: `python codigo/portal_scraping.py --gore AB080 --etiqueta 2027-04-10`.
- [ ] Revise `salidas/robots_bloqueadas_2027-04-10.csv` (si existe): son páginas que el sitio pide no visitar. No use `--ignorar-robots` salvo con una justificación escrita en el informe.
- [ ] Los documentos que no se puedan descargar se dejan a mano en `documentos_manuales/` (`AB080_erd.pdf`, `AB080_cuenta_publica.pdf`) y se repite `python codigo/ods_documentos.py --etiqueta 2027-04-10`.

### 2b. Revisión manual (1 día; ver `PROTOCOLO_REVISION_MANUAL.md`)

- [ ] Abrir `salidas/revision_manual_2027-04-10.xlsx` (la crea `recolectar`) y resolver cada caso pendiente: celdas ER y SD del Portal, documentos no disponibles, documentos escaneados, sitios sin menciones y la muestra de control.
- [ ] Registrar en la planilla cada búsqueda manual y cada mención hallada a mano.
- [ ] Confirmar los «No disponible» con una segunda persona.
- [ ] Generar la planilla de codificación: `python ejecutar_todo.py plantilla --etiqueta 2027-04-10` (valida la revisión e incluye las menciones manuales).

### 3. Comprobar el buscador (30 minutos)

- [ ] En la hoja `Muestra_verificacion` del Excel de codificación (5 GORE elegidos al azar con semilla fija), una segunda persona repite la búsqueda en el sitio y anota el conteo. Criterio: ≥ 90 % de coincidencias (±1).

### 4. Codificar (dos personas, 1 a 2 días)

Archivo: `salidas/codificacion_ods_2027-04-10.xlsx`. Las reglas están en la hoja `Instrucciones` y en el apartado «Divulgación de los ODS» del README.

- [ ] Cada persona llena **solo su columna** (codificador 1 o 2), sin mirar la otra: hojas `Menciones`, `Documentos` y `Mapa_17_ODS`.
- [ ] Revise el acuerdo: `python codigo/ods_codificacion.py kappa salidas/codificacion_ods_2027-04-10.xlsx`. Si algún κ es menor que 0,60, discutan los criterios y recodifiquen antes de seguir.
- [ ] Discutan los desacuerdos y llenen las columnas de consenso («Consenso final» y la fila «consenso» del mapa).
- [ ] Si usan inteligencia artificial como apoyo, declárenlo en el informe y mantengan siempre una codificación humana independiente.

### 5. Cerrar, analizar y publicar (1 hora)

```bash
python ejecutar_todo.py cerrar 2027-1 --etiqueta 2027-04-10 \
       --fecha-scraping "10 de abril de 2027" --fecha-ods "12 al 20 de abril de 2027"
```

Esto deja:

- `mediciones/2027-1/` — los datos de la ronda en formato estándar (ver `DICCIONARIO_DATOS.md`), la planilla codificada, los archivos crudos y `manifiesto.json` con la huella SHA-256 de cada archivo, las fechas y las versiones del software.
- `resultados/2027-1/` — `analisis_2027-1.xlsx` (con la comparación con la ronda anterior) y las figuras.
- `resultados/serie_rondas.csv` y `resultados/evolucion_rondas.png` — los indicadores de todas las rondas.
- `docs/index.html` — el visor actualizado.

- [ ] Lea la hoja `Resumen` del análisis y compare con la ronda anterior. Cambios grandes en un GORE suelen ser cambios del sitio: verifíquelos en el sitio antes de interpretarlos.
- [ ] Anote la ronda en `CHANGELOG.md` (fechas, quién recolectó y codificó, cambios en `gores.csv`, problemas).
- [ ] Publique la versión (ver `PUBLICAR.md`): commit, etiqueta `ronda-2027-1` y nueva versión en Zenodo.

## Reglas que no se cambian

1. **Una ronda cerrada no se edita.** Si hay un error, se corrige la planilla, se vuelve a cerrar con `--forzar` y se explica en `CHANGELOG.md`. `python ejecutar_todo.py verificar 2027-1` detecta cualquier cambio posterior.
2. **Dos codificadores independientes** y consenso documentado en cada ronda.
3. **Mismos términos, categorías y reglas de puntaje** que en `2026-1`, salvo cambio de versión mayor.
4. **Solo información pública.** No se guarda el contenido de las tablas del Portal (puede tener datos personales), solo su existencia y tamaño.
5. **Respeto de robots.txt** y pausas de 1 a 2,5 segundos entre solicitudes.
