# Publicar el repositorio y obtener un DOI

Se hace **una vez** (pasos 1 a 3) y luego, en cada ronda, solo el paso 4.

## 1. Crear el repositorio en GitHub

1. Cree una cuenta en <https://github.com> (gratuita) o use la del grupo de investigación.
2. *New repository* → nombre `gore-transparencia-ods` → **Public** → sin README (ya existe) → *Create*.
3. En la carpeta del proyecto (Terminal):

```bash
git init
git add .
git commit -m "Versión 1.1.0: rondas de medición reproducibles"
git branch -M main
git remote add origin https://github.com/Leandraslzrp/gore-transparencia-ods.git
git push -u origin main
```

`config/contacto.txt`, `salidas/` y `cache/` no se suben (están en `.gitignore`).

## 2. Visor y pruebas automáticas

- **Visor**: *Settings → Pages → Deploy from a branch → main → /docs → Save*. En unos minutos queda en `https://Leandraslzrp.github.io/gore-transparencia-ods/`.
- **Pruebas**: el archivo `.github/workflows/pruebas.yml` corre las pruebas en cada cambio (pestaña *Actions*). Una marca verde indica que la ronda del paper se sigue reproduciendo.

## 2b. Correo de contacto para las Actions

Las tareas automáticas se identifican ante los sitios con un correo. En GitHub: *Settings → Secrets and variables → Actions → pestaña Variables → New repository variable*, nombre `CONTACTO_INVESTIGACION`, valor su correo.

## 3. Conectar con Zenodo (DOI permanente)

1. Entre a <https://zenodo.org> con la cuenta de GitHub.
2. *Account → GitHub* → active el interruptor del repositorio `gore-transparencia-ods`.
3. En GitHub: *Releases → Draft a new release* → etiqueta `v1.1.0` → título «Versión 1.1.0» → *Publish release*.
4. Zenodo archiva esa versión y entrega un DOI (por ejemplo `10.5281/zenodo.1234567`). Use el **DOI de concepto** (el que agrupa todas las versiones) para citar en el paper y agregue ese DOI a `CITATION.cff` y al README.

Zenodo toma los autores, la licencia y las palabras clave de `.zenodo.json`. Revise que las afiliaciones y ORCID estén completos antes del primer *release*.

## 4. En cada ronda

```bash
git add mediciones/2027-1 actualizaciones resultados/2027-1 resultados/serie_rondas.csv resultados/evolucion_rondas.png docs CHANGELOG.md config datos/referencia_cplt.csv
git commit -m "Ronda 2027-1"
git tag ronda-2027-1
git push && git push --tags
```

Luego un *release* nuevo en GitHub (por ejemplo `v1.1.0-ronda-2027-1`): Zenodo le asigna un DOI propio, de modo que cada ronda queda citable y congelada.

## Versiones del código

- **Parche** (1.1.1): correcciones que no cambian ningún resultado.
- **Menor** (1.2.0): funciones nuevas; las rondas anteriores dan las mismas cifras (las pruebas lo verifican).
- **Mayor** (2.0.0): cambia el método (términos, categorías, reglas de puntaje o de codificación). La serie se corta y debe explicarse.

## Declaración de disponibilidad (para el paper)

> El código, los datos de cada ronda de medición (con huellas SHA-256 y manifiesto de versiones), el protocolo de codificación y el visor están disponibles en https://github.com/Leandraslzrp/gore-transparencia-ods y archivados en Zenodo (DOI: 10.5281/zenodo.XXXXXXX) bajo licencias MIT (código) y CC BY 4.0 (datos). Las cifras del artículo corresponden a la ronda 2026-1 y se reproducen sin conexión con `python ejecutar_todo.py pruebas`.
