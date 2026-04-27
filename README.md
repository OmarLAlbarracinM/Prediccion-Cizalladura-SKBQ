# Prediccion de vientos - SKBO (METAR)

Modelo predictivo local de viento para el Aeropuerto Internacional El Dorado (SKBO)
usando series historicas METAR. Proyecto de grado - MIAD, Universidad de los Andes.

**Entidad de contexto:** Fuerza Aeroespacial Colombiana (SIMFAC / DINAV)  
**Estado:** WIP - fase de experimentacion de modelos

## Estructura

```
notebooks/      notebooks de analisis y modelado (numerados por etapa)
pipelines/      scripts reproducibles de ingesta y preprocesamiento
data/
  raw/          datos crudos (versionados con DVC, no en git)
  Processed/    datasets procesados (versionados con DVC)
  NewData/      datos nuevos para ingesta incremental
referencias/    repos externos de referencia (no commiteados)
```

## Notebooks

| # | Archivo | Descripcion |
|---|---------|-------------|
| 01 | `01_exploracion.ipynb` | EDA del dataset METAR crudo |
| 02 | `02_preprocesamiento.ipynb` | Limpieza, parsing y extraccion de variables |
| 03 | `03_transformacion_variables.ipynb` | Transformacion vectorial del viento (u, v), resample horario |
| 04 | `04_modelos_var_lstm_skbo.ipynb` | Modelos VAR y LSTM baseline para SKBO |
| 05 | `05_modelos_lstm_gru_optimizado.ipynb` | LSTM y GRU con keras-tuner, mejor resultado: H1=29.2 grados |
| 06 | `06_modelo_seq2seq_multihorizonte.ipynb` | Seq2Seq con 6 modelos independientes y custom angular loss |
| 07 | `07_experimento_covariables.ipynb` | Experimento: temperatura, rocio y QNH como features |

## Pipelines

```bash
python pipelines/ingestion_new_data.py
python pipelines/preprocesamiento_metar.py
```

## Datos (DVC)

Los datos no se almacenan en git, estan versionados con DVC con remote local.

```bash
dvc pull
dvc push
```

## Metricas objetivo (RAC 12)

| Variable | Limite | Mejor resultado actual |
|----------|--------|----------------------|
| Velocidad | MAE <= 5 kt | ~1.6 kt (cumple todos los modelos) |
| Direccion | MAE <= 30 grados | 29.2 grados en H1 (H2-H6 sin resolver) |

## Dependencias

```bash
uv sync
```
