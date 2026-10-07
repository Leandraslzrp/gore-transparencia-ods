# Registro de cambios

Versiones del código y del protocolo de medición (ver `documentacion/PUBLICAR.md`).

## [2.0.0] — 2026-10-07

Repositorio dedicado a la medición replicable. Contiene el código, el protocolo de rondas, el protocolo de revisión manual, las plantillas y las pruebas. El método de medición no cambia respecto de la versión usada en el artículo.

### Cambiado
- Los datos de las rondas (`mediciones/`, `resultados/`), los resultados del artículo y los PDF aportados a mano ya no se versionan aquí: quedan en el computador de quien mide y se publican aparte.
- El visor web y las mediciones del Portal entre rondas pasan a un proyecto separado.
- `ejecutar_todo.py`: comandos `recolectar`, `plantilla`, `cerrar`, `analizar`, `verificar` y `pruebas`.
- `documentacion/PROTOCOLO_RONDAS.md`: centrado en la replicación, con roles, criterios para elegir la fecha y corrección de rondas cerradas.
- Las planillas que genera el código ya no tienen hoja de instrucciones ni filas de ejemplo (las reglas están en el README y en los protocolos), y la hoja Documentos de la planilla de codificación ya no muestra la huella SHA-256: `cerrar` la toma directamente de la recolección (`ods_documentos_FECHA.csv`), así que sigue registrada en `mediciones/RONDA/ods_documentos.csv`.

### Agregado
- `plantillas/`: planillas de revisión manual y de codificación en blanco.
- `tests/datos/`: salidas de ejemplo de la recolección automática (29-09-2026); las pruebas simulan dos rondas completas sin internet.
- README con resumen en inglés.

## Versiones anteriores

La versión 1.x (septiembre y octubre de 2026) incluía, además del código, los datos de la ronda 2026-1 del artículo, el visor y sus mediciones mensuales del Portal.
