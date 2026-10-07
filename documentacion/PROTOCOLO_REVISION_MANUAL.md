# Protocolo de revisión manual

El código encuentra la mayor parte de la información, pero no toda. En la ronda 2026-1, por ejemplo:

- recuperó 22 de las 32 menciones web de los ODS; las otras 10 se hallaron a mano porque los buscadores internos de algunos sitios no indexan todas sus páginas;
- descargó 25 de los 30 documentos analizados; los otros 5 los aportó el equipo porque el sitio los bloqueaba o no los enlazaba;
- la cuenta pública 2025 de La Araucanía se registró como «no disponible» porque estaba publicada en un visor embebido (Heyzine) y no como archivo. Se encontró en una revisión posterior.

Este protocolo hace que esa revisión manual sea **sistemática, registrada y repetible**: se revisan siempre los mismos tipos de casos, con los mismos pasos, y cada búsqueda queda anotada.

## Cuándo se hace

Entre la recolección automática y la codificación (paso 2b de `PROTOCOLO_RONDAS.md`):

```
recolectar  →  REVISIÓN MANUAL  →  plantilla de codificación  →  codificar  →  cerrar
```

`python ejecutar_todo.py recolectar` genera, al final, `salidas/revision_manual_FECHA.xlsx` con los casos pendientes. Calcule **un día de trabajo** para una persona, más una hora de una segunda persona para confirmar los «no disponible».

## La planilla de revisión

| Hoja | Qué contiene | Quién la llena |
|---|---|---|
| Pendientes | Un caso por fila, generado por el código, con el tipo, el GORE y qué revisar | Revisor 1 (y Revisor 2 para confirmar los «no disponible») |
| Menciones_manuales | Cada página web con mención de los ODS hallada a mano | Revisor 1 |
| Busquedas_manuales | Cada búsqueda hecha a mano, **aunque no encuentre nada** | Revisor 1 |

Las celdas amarillas se llenan; las filas grises son ejemplos. El resultado de cada caso se elige de una lista:

| Resultado | Cuándo usarlo | Evidencia obligatoria |
|---|---|---|
| Confirmado (sin cambios) | La revisión confirma lo que registró el código | No |
| Encontrado a mano | Se halló el documento o la información que el código no encontró | Sí: URL o archivo |
| Corregido | El código se equivocó (por ejemplo, una celda ER que en realidad tiene datos) | Sí: URL o captura |
| No disponible (confirmado por 2) | Dos personas, por separado, no lo encontraron | Firma del Revisor 2 |
| Solo video | El documento existe solo como video | Sí: URL del video |
| No aplica | El caso no corresponde (por ejemplo, el GORE no tiene esa obligación) | Nota |

## Tipos de casos y qué hacer

### 1. Portal de Transparencia: celdas ER y SD

1. Abra la ficha del GORE: `https://www.portaltransparencia.cl/PortalPdT/directorio-de-organismos-regulados/?org=CÓDIGO`.
2. Entre a la categoría y al período más reciente, como lo haría una persona.
3. **ER** (error o ítem inexistente): si la página carga y tiene datos, es una falla del recorrido. Repita ese GORE con `python codigo/portal_scraping.py --gore CÓDIGO --etiqueta FECHA` y marque «Corregido».
4. **SD** (sin datos): confirme que dice «0 resultados», «no publica información» o está vacía. Revise hasta 3 períodos anteriores.
5. Si cambia el estado, guarde una captura en `salidas/capturas/CÓDIGO_CATEGORÍA_manual.png` y anótela como evidencia.

### 2. Documentos: ERD y cuenta pública «No disponible» o «Solo video»

Busque en este orden y **anote cada lugar revisado** en Busquedas_manuales:

1. Las URL de `config/gores.csv`, por si solo cambió la dirección.
2. Las secciones del sitio del GORE: «Cuenta pública», «Gestión», «Documentos», «Planificación», «Transparencia».
3. Noticias del sitio cercanas a la fecha de la cuenta pública (normalmente entre mayo y julio).
4. **Visores embebidos** (Heyzine, Issuu, Calaméo, FlipHTML5, Google Drive, Scribd). En Chrome: clic derecho → *Inspeccionar* → pestaña *Red* (Network) → filtrar por `pdf` → recargar la página; el archivo original suele aparecer ahí. Si no se puede descargar, anote la URL del visor.
5. Google: `site:dominio-del-gore.cl "cuenta pública" 2025` y `site:dominio-del-gore.cl "estrategia regional de desarrollo"`.
6. YouTube o redes del GORE, si es una cuenta pública en video.
7. Si nada funciona, la sección de Transparencia Activa del Portal (categoría de documentos de planificación o de gestión).

Si lo encuentra:

- Guarde el PDF en `documentos_manuales/CÓDIGO_erd.pdf` o `documentos_manuales/CÓDIGO_cuenta_publica.pdf`.
- Si ya hay un archivo con ese nombre, reemplácelo solo si el nuevo es más reciente y anótelo en la Nota.
- Repita la lectura: `python codigo/ods_documentos.py --gore CÓDIGO --etiqueta FECHA`.
- Actualice la URL en `config/gores.csv` y anote el cambio en la Bitácora de la ronda.

**«No disponible» solo se acepta si dos personas lo buscaron por separado**, siguiendo esta lista, y ninguna lo encontró. Si existe solo en video, use «Solo video». Opcional: pedirlo por Ley de Transparencia (solicitud de acceso a la información) y anotar el número de la solicitud.

### 3. Documentos con poco texto por página

Si un documento tiene menos de 300 caracteres por página, probablemente es una imagen escaneada o una presentación.

1. Confirme que el código usó OCR (columna `metodo` de `ods_documentos_FECHA.csv`).
2. Abra el PDF y busque a mano los términos (Ctrl+F; si no es seleccionable, revise los títulos y las láminas).
3. Si encuentra un término que el código no detectó, marque «Corregido» y anote la página.

### 4. Sitios web sin menciones verificadas

Para cada GORE donde el código no verificó ninguna mención:

1. Use el buscador del sitio con cada término del protocolo: «ODS», «Objetivos de Desarrollo Sostenible», «Agenda 2030» y «ODS 16».
2. Use Google con cada término: `site:dominio-del-gore.cl "ODS"` (repita para cada término).
3. Revise la sección de noticias de los últimos 3 años con la búsqueda del navegador (Ctrl+F).
4. **Verifique cada resultado**: abra la página y confirme que el término está en el texto (no solo en un menú o en una etiqueta). «ODS» debe ir en mayúsculas y como palabra completa.
5. Cada mención verificada va a la hoja Menciones_manuales con su URL, título, fecha, términos y cómo se encontró.
6. Cada búsqueda va a Busquedas_manuales, aunque no dé resultados: así se puede reportar el esfuerzo y otra persona puede repetirla.

### 5. Páginas bloqueadas por robots.txt

El código no visita las páginas que el sitio pide no recorrer. Revíselas a mano solo si son públicas y relevantes (por ejemplo, una noticia o un documento). No use `--ignorar-robots` para resolver esto.

### 6. Control de calidad: muestra de documentos «Sin mención»

El código elige al azar 5 documentos clasificados «Sin mención» (semilla fija 2026, para que la muestra sea reproducible). Ábralos y busque a mano los términos. Si todos se confirman, el código es confiable para esa ronda. Si alguno tenía menciones, márquelo «Corregido», revise el resto de los documentos de ese tipo y anótelo en la Bitácora.

## Reglas comunes

- **Mismos términos y criterios que el código.** La revisión manual completa la búsqueda; no cambia las reglas.
- **Ventana de búsqueda:** la misma de la ronda. Una página o documento publicado después del cierre de la recolección se anota, pero se usa en la ronda siguiente.
- **Todo con evidencia:** URL, archivo o captura. Lo que no se puede mostrar no se registra como hallazgo.
- **La revisión manual no clasifica.** Solo encuentra y verifica. La clasificación retórica o sustantiva se hace después, en la planilla de codificación, con dos codificadores.

## Cerrar la revisión

```bash
python ejecutar_todo.py plantilla --etiqueta FECHA
```

El código valida la planilla y no sigue si:

- hay casos sin resultado;
- hay «No disponible» sin la confirmación del Revisor 2;
- hay hallazgos sin evidencia;
- hay menciones manuales sin URL o sin términos.

Si todo está completo, exporta tres archivos a `salidas/`:

- `revision_manual_FECHA.csv`
- `ods_menciones_manuales_FECHA.csv`
- `busquedas_manuales_FECHA.csv`

Luego genera la planilla de codificación con las menciones manuales incluidas (identificador `M001`, `M002`…). Al cerrar la ronda, los tres archivos quedan en `mediciones/RONDA/crudos/` con su huella SHA-256.

## Qué reportar en el informe o paper

- Cuántas menciones encontró el código y cuántas se hallaron a mano (por ejemplo: «22 de 32 automáticas; 10 manuales»).
- Cuántos documentos descargó el código y cuántos aportó el equipo, y por qué.
- Qué documentos no estaban disponibles y cómo se confirmó (dos revisores; solo video).
- El resultado del control de calidad de documentos «Sin mención».
