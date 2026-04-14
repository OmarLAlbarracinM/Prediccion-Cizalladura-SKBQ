# Pipelines

## Preprocesamiento METAR

Pipeline basado en `docs/notebooks/02_preprocesamiento.ipynb` para generar
`data/raw/DATOS_PROCESADOS.csv` a partir de `data/raw/DATOS_CRUDOS.csv`.

### Uso

```bash
python pipelines/preprocesamiento_metar.py
```

Opcionalmente puedes especificar rutas:

```bash
python pipelines/preprocesamiento_metar.py --input data/raw/DATOS_CRUDOS.csv --output data/raw/DATOS_PROCESADOS.csv
```

## Ingesta de nuevos datos

Une `data/raw/DATOS_CRUDOS.csv` con `data/NewData/skbo.csv`, crea un respaldo
del dataset original, actualiza el archivo principal y versiona con DVC.

### Uso

```bash
python pipelines/ingestion_new_data.py
```

Opcionalmente puedes especificar rutas:

```bash
python pipelines/ingestion_new_data.py --raw data/raw/DATOS_CRUDOS.csv --new data/NewData/skbo.csv --backup-dir data/raw
```
