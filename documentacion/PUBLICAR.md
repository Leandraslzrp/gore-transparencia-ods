# Publicar una versión y obtener un DOI

Este repositorio contiene el código y el protocolo de medición. Los datos de cada ronda (`mediciones/`, `resultados/`, `salidas/` y los PDF de `documentos_manuales/`) no se suben: quedan en el computador de quien mide y se publican aparte, por ejemplo como conjunto de datos en Zenodo.

## 1. Subir cambios del código

```bash
python ejecutar_todo.py pruebas      # deben terminar en OK
git add -A
git status --short                   # revise qué se va a subir
git commit -m "Descripción breve del cambio"
git push
```

En cada cambio, GitHub corre las pruebas y revisa el estilo del código (pestaña *Actions*; `.github/workflows/pruebas.yml`). Una marca verde indica que todo está en orden.

## 2. Conectar con Zenodo (una vez)

1. Entre a <https://zenodo.org> con la cuenta de GitHub.
2. En su nombre → *GitHub*, active el interruptor del repositorio `gore-transparencia-ods`.

Zenodo toma los autores, la licencia y las palabras clave de `.zenodo.json`. Revise que las afiliaciones y los ORCID estén completos antes de la primera versión.

## 3. Publicar una versión

1. Actualice `version` y `date-released` en `CITATION.cff` y agregue la versión a `CHANGELOG.md`.
2. En GitHub: *Releases → Draft a new release*, etiqueta `vX.Y.Z`, título «Versión X.Y.Z» y *Publish release*.
3. Zenodo archiva esa versión y le asigna un DOI. Para citar, use el **DOI de concepto** (el que agrupa todas las versiones) y agréguelo a `CITATION.cff` y al README.

## Números de versión

- **Parche** (2.0.1): correcciones que no cambian ningún resultado.
- **Menor** (2.1.0): funciones nuevas que no cambian el método; las pruebas lo verifican.
- **Mayor** (3.0.0): cambia el método (términos, categorías, reglas de puntaje o de codificación). Las rondas dejan de ser comparables, y hay que explicarlo.
