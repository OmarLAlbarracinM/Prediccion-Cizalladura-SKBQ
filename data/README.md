# data/ — Datos del Proyecto

## Descripción

Almacena todos los datasets del proyecto de predicción de cizalladura
del viento para el aeropuerto SKBO. Los datos fluyen a través de tres
etapas (crudo → procesado → ventana temporal) antes de ser consumidos
por los pipelines de entrenamiento e inferencia del modelo LSTM.

## Estructura

```
data/
├── raw/                         # Datos en su estado original
│   ├── DATOS_CRUDOS.csv         # Dataset maestro con todos los reportes METAR históricos
│   ├── DATOS_CRUDOS.csv.dvc     # Archivo de tracking de DVC para versionado
│   ├── DATOS_PROCESADOS.csv.dvc # Tracking DVC del dataset procesado
│   ├── skbo_metar.xlsx          # Fuente original de datos METAR en formato Excel
│   └── .gitignore               # Excluye los CSV grandes de Git (se rastrean con DVC)
│
├── Processed/                   # Datos transformados listos para el modelo
│   ├── DATOS_PROCESADOS.csv     # METAR limpio con variables meteorológicas extraídas
│   ├── DATOS_ENTRENAMIENTO.csv  # Dataset completo usado para entrenamiento del LSTM
│   ├── skbo_ventana.csv         # Ventana temporal descargada desde la API SIMFAC
│   ├── skbo_ventana_transformada.csv  # Ventana con feature engineering y escalado
│   └── prediccion_lstm.csv      # Resultado de la última predicción del pipeline
│
└── NewData/                     # Datos nuevos pendientes de integrar
    └── (archivos CSV/XLSX descargados desde SIMFAC para ingesta)
```

## Flujo de datos

```
     skbo_metar.xlsx (fuente Excel)
           │
           ▼
     DATOS_CRUDOS.csv ──────────────────────────┐
           │                                     │ ingestion_new_data.py
           │ preprocesamiento_metar.py           │ (une nuevos datos)
           ▼                                     ▼
     DATOS_PROCESADOS.csv               NewData/*.csv
           │
           │ preparar_datos_lstm.py
           ▼
     DATOS_ENTRENAMIENTO.csv
           │
           │ (entrenamiento del modelo en notebooks)
           ▼
     models/best_model_20h.h5 + scaler_X.pkl + scaler_y.pkl
```

Para **inferencia en tiempo real** (via pipelines o API):

```
     API SIMFAC (descarga automática)
           │
           │ ventana_metar.py / preprocessing.py
           ▼
     skbo_ventana.csv
           │
           │ preparar_datos_lstm.py
           ▼
     skbo_ventana_transformada.csv
           │
           │ prediccion_lstm.py
           ▼
     prediccion_lstm.csv
```

## Archivos principales

### `raw/DATOS_CRUDOS.csv`

Dataset maestro que contiene **todos los reportes METAR** del aeropuerto
SKBO desde 2013 hasta la fecha más reciente ingresada. Cada fila es un
reporte METAR con las columnas originales del sistema SIMFAC, incluyendo
`FECHA_REPORTE`, `HORA_REPORTE`, `TIPO_REPORTE` y `TEXTO_REPORTE`.

Este archivo se versiona con **DVC** (Data Version Control). El archivo
`.dvc` correspondiente se rastrea con Git, mientras que el CSV real se
almacena en el backend de DVC.

### `Processed/DATOS_PROCESADOS.csv`

Resultado de aplicar el pipeline de preprocesamiento (`preprocesamiento_metar.py`)
sobre `DATOS_CRUDOS.csv`. Contiene variables meteorológicas extraídas:
aeródromo, hora zulú, viento (dirección + velocidad), visibilidad,
nubosidad, temperatura/rocío, presión y fenómenos.

### `Processed/DATOS_ENTRENAMIENTO.csv`

Dataset completo con todas las features de ingeniería aplicadas, listo
para ser consumido por el notebook de entrenamiento del modelo LSTM.

### `Processed/skbo_ventana.csv`

Ventana temporal de reportes METAR (típicamente las últimas 50 horas)
descargada directamente desde la API de SIMFAC mediante
`ventana_metar.py`. Se usa como entrada para la cadena de inferencia
del pipeline.

### `Processed/skbo_ventana_transformada.csv`

Resultado de aplicar `preparar_datos_lstm.py` sobre `skbo_ventana.csv`.
Contiene las 5 features del modelo (`dir_sin`, `dir_cos`, `intensidad_kt`,
`temperatura`, `rocio`) ya normalizadas con `StandardScaler`.

### `Processed/prediccion_lstm.csv`

Archivo de salida del pipeline `prediccion_lstm.py`. Contiene las
predicciones del modelo (dirección, intensidad, indicador de cizalladura
y causa) para las próximas 6 horas.

## Versionado con DVC

Los archivos CSV grandes se versionan con [DVC](https://dvc.org/) para
no sobrecargar el repositorio Git. El flujo es:

```bash
# Después de actualizar DATOS_CRUDOS.csv
dvc add data/raw/DATOS_CRUDOS.csv
git add data/raw/DATOS_CRUDOS.csv.dvc data/raw/.gitignore
git commit -m "data: actualizar DATOS_CRUDOS.csv"
dvc push  # sube al backend remoto de DVC
```

El pipeline `ingestion_new_data.py` automatiza este flujo: hace backup,
une los datos nuevos, deduplica y ejecuta `dvc add`.

## Infraestructura

- **DVC backend:** configurado en `.dvc/` (carpeta raíz del proyecto).
  La configuración define el almacenamiento remoto donde se guardan los
  archivos versionados.
- **`.gitignore` en `raw/`:** asegura que los CSV grandes rastreados
  por DVC no se suban a Git por accidente.
- **Convención de nombres:** los archivos que son residuos de
  experimentos (sufijos `_test`, `_v2`, `_final`) fueron eliminados
  durante la limpieza del repositorio. Solo se conservan los archivos
  activos del flujo de producción.
