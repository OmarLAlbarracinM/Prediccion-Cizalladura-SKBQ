# Predicción de vientos — SKBQ (METAR)

**Propósito**
Modelo predictivo de condiciones de viento y detección temprana de eventos críticos (ej. cizalladura) para el Aeropuerto Internacional Ernesto Cortissoz (SKBQ) usando series históricas METAR.

**Estado**: WIP — prototipo de ingestión, preprocesamiento y modelos baseline (persistence, XGBoost, LSTM).

---

## Contenido rápido

* `data/` — raw, staged, processed (los datos crudos no se guardan en Git; se versionan con DVC).
* `pipelines/` — pipelines reproducibles (ingesta de nuevos datos y preprocesamiento METAR).
* `docs/` — diagramas, data dictionary y decisiones de diseño - análisis exploratorio y pruebas reproductibles.
* `.dvc/`, `dvc.yaml` — pipeline y metadatos DVC.

---

## Requisitos

* Python 3.9+ (recomendado 3.10)
* pip / conda
* dvc (instalación básica para local): `pip install dvc`
* pandas, pyarrow (si conviertes a parquet), scikit-learn, xgboost, torch/keras (si usas LSTM), jupyterlab.

Ejemplo (virtualenv):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Datos (clave)

* Archivo principal (ejemplo): `data/raw/DATOS_CRUDOS.csv`
* **No comitees datos grandes** en Git. Usar DVC con remote local (disco o NAS).
* Ingesta de nuevos datos: usa el script `pipelines/ingestion_new_data.py` para unir
  `data/raw/DATOS_CRUDOS.csv` con `data/NewData/skbo.csv`, crear respaldo y versionar con DVC.
* Flujo recomendado:

  1. `dvc init` (una sola vez)
  2. `dvc remote add -d localremote /ruta/al/remote`  # remote local
  3. `dvc add data/raw/DATOS_CRUDOS.csv`
  4. `git add data/raw/DATOS_CRUDOS.csv.dvc .gitignore && git commit -m "track datos crudos via dvc"`
  5. `dvc push`

**Si clonas el repo en otra máquina:**

```bash
git clone <repo>
dvc remote modify localremote path /ruta/del/remote/en/esta/maquina  # si difiere
dvc pull
```

---

## Pipelines

### Consulta de METAR desde API

Consulta la API de SIMFAC para descargar datos METAR de un aeropuerto (OACI) en un rango de fechas específico o de los últimos N días. Guarda los resultados en `data/NewData/{oaci}.csv` por defecto, listos para ser usados por el pipeline de ingestión.

```bash
# Descargar datos para SKBQ para un rango de fechas
python pipelines/consultar_api_metar.py --oaci SKBQ --start 2024-06-01 --end 2024-06-30

# Descargar datos de los últimos 14 días para SKBO
python pipelines/consultar_api_metar.py --oaci SKBO --days 14
```

### Descarga de ventana de datos

Un script especializado que descarga una ventana de horas de datos METAR hacia atrás desde una fecha de fin. Es útil para obtener los datos más recientes para predicción o análisis específico.

```bash
# Descargar las últimas 50 horas de datos para SKBQ
python pipelines/ventana_metar.py --oaci SKBQ --hours 50

# Descargar 24 horas de datos terminando en una fecha y hora específicas
python pipelines/ventana_metar.py --oaci SKBO --end "2024-06-30 12:00" --hours 24
```

### Ingesta de nuevos datos

Une el dataset crudo con nuevos datos desde `data/NewData/skbo.csv`, deduplica por
`FECHA_REPORTE`, `HORA_REPORTE`, `TIPO_REPORTE`, actualiza `data/raw/DATOS_CRUDOS.csv`
y versiona con DVC.

```bash
python pipelines/ingestion_new_data.py
```

Opcionalmente puedes especificar rutas:

```bash
python pipelines/ingestion_new_data.py --raw data/raw/DATOS_CRUDOS.csv --new data/NewData/skbo.csv --backup-dir data/raw
```

### Preprocesamiento METAR

Genera `data/raw/DATOS_PROCESADOS.csv` a partir de `data/raw/DATOS_CRUDOS.csv`.

```bash
python pipelines/preprocesamiento_metar.py
```

Opcionalmente puedes especificar rutas:

```bash
python pipelines/preprocesamiento_metar.py --input data/raw/DATOS_CRUDOS.csv --output data/raw/DATOS_PROCESADOS.csv
```

---
