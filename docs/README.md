# docs/ — Documentación y Notebooks

## Descripción

Carpeta de documentación del proyecto. Contiene dos subcarpetas de
notebooks de Jupyter que representan las fases de investigación y
experimentación del proyecto de predicción de cizalladura de viento.

## Estructura

```
docs/
├── notebooks/                    # Notebooks maduros del flujo principal
│   ├── 01_exploracion.ipynb      # Análisis exploratorio de datos (EDA)
│   ├── 02_preprocesamiento.ipynb # Pipeline de limpieza y transformación
│   └── 03_transformacion_variables.ipynb  # Feature engineering
│
└── experimentos_notebooks/       # Notebooks de pruebas de hipótesis y modelos
    ├── 00_proyecto_de_grado.ipynb             # Notebook principal de la tesis
    ├── 01_prueba_lstm_base.ipynb              # Primera prueba LSTM base
    ├── 02_prueba_lstm_exp_e.ipynb             # Experimento con variante E
    ├── 03_prueba_lstm_exp_e2.ipynb            # Segunda variante E2
    ├── 04_prueba_lstm_gru.ipynb               # Comparación LSTM vs GRU
    ├── 05_prueba_lstm_omar.ipynb              # Exploración personal
    ├── 06_prueba_lstm_data_completa.ipynb      # LSTM con dataset completo
    ├── 07_prueba_lstm_uv.ipynb                # LSTM con componentes U-V del viento
    ├── 08_prueba_lstm_pred_cizalladura.ipynb  # ★ Notebook fuente de los pipelines
    └── 09_api_metar_pruebas.ipynb             # Pruebas de la API SIMFAC
```

## Subcarpetas

### `notebooks/` — Flujo de análisis principal

Estos tres notebooks representan el **pipeline de investigación maduro**
que se ejecutó de forma secuencial para entender y preparar los datos:

| # | Notebook | Qué hace | Por qué se hizo |
|---|----------|----------|-----------------|
| 01 | `01_exploracion.ipynb` | Análisis exploratorio de datos (EDA): distribuciones de viento, temperatura, rocío, estacionalidad, outliers y patrones temporales. | Para entender el comportamiento del viento en SKBO antes de modelar. |
| 02 | `02_preprocesamiento.ipynb` | Limpieza del dataset METAR: eliminación de registros NIL, normalización de fechas, tokenización y extracción de variables. | Sirvió como prototipo para el pipeline `preprocesamiento_metar.py`. |
| 03 | `03_transformacion_variables.ipynb` | Feature engineering: conversión de dirección a componentes seno/coseno, capping de outliers, resampleo horario. | Sirvió como prototipo para `preparar_datos_lstm.py`. |

### `experimentos_notebooks/` — Pruebas de arquitecturas y modelos

Colección de **experimentos iterativos** realizados durante la maestría
para llegar al modelo final. Están numerados en orden cronológico de
creación:

| # | Notebook | Qué prueba | Resultado |
|---|----------|-----------|-----------|
| 00 | `00_proyecto_de_grado.ipynb` | Notebook integral de la tesis: incluye todo el flujo desde la exploración hasta la evaluación final. | Documento de referencia académica. |
| 01 | `01_prueba_lstm_base.ipynb` | Primera implementación de un LSTM vanilla para predecir velocidad del viento. | Baseline funcional pero con errores altos en dirección. |
| 02 | `02_prueba_lstm_exp_e.ipynb` | Variación de hiperparámetros (épocas, learning rate). | Mejora marginal. |
| 03 | `03_prueba_lstm_exp_e2.ipynb` | Segunda variación con dropout más agresivo. | Reducción de overfitting pero predicciones más conservadoras. |
| 04 | `04_prueba_lstm_gru.ipynb` | Comparación de arquitectura LSTM vs GRU. | LSTM superior para este caso de uso. |
| 05 | `05_prueba_lstm_omar.ipynb` | Exploración personal con diferentes ventanas temporales. | Ventana de 20 horas como óptima. |
| 06 | `06_prueba_lstm_data_completa.ipynb` | Entrenamiento con el dataset completo (2013-2024). | Mejora significativa con más datos históricos. |
| 07 | `07_prueba_lstm_uv.ipynb` | Representación del viento con componentes U-V (meteorológicas) en lugar de seno/coseno. | Seno/coseno más estable numéricamente. |
| 08 | `08_prueba_lstm_pred_cizalladura.ipynb` | **★ Notebook final.** Modelo LSTM con `circular_loss`, predicción multivariable (dirección + intensidad) y análisis de cizalladura. | Este notebook es la fuente de los pipelines de producción. |
| 09 | `09_api_metar_pruebas.ipynb` | Pruebas de integración con la API de SIMFAC para descarga de METAR en tiempo real. | Validó la viabilidad de la alimentación automática de datos. |

## Relación con la infraestructura

Los notebooks de `docs/` son artefactos de **investigación**. No se
ejecutan en producción. Sin embargo, los pipelines de `pipelines/` y el
código de `app/` fueron derivados directamente de ellos:

```
docs/notebooks/02_preprocesamiento.ipynb
    └──→ pipelines/preprocesamiento_metar.py

docs/notebooks/03_transformacion_variables.ipynb
    └──→ pipelines/preparar_datos_lstm.py

docs/experimentos_notebooks/08_prueba_lstm_pred_cizalladura.ipynb
    ├──→ pipelines/prediccion_lstm.py
    ├──→ app/model.py (ModelManager)
    └──→ app/preprocessing.py (parsing METAR)

docs/experimentos_notebooks/09_api_metar_pruebas.ipynb
    └──→ pipelines/consultar_api_metar.py
```

## Convenciones de nombres

- Los notebooks usan prefijo numérico `##_` para indicar orden lógico.
- Los nombres usan `snake_case` sin espacios ni caracteres especiales.
- El notebook `08_prueba_lstm_pred_cizalladura.ipynb` es el más
  importante: contiene la definición de la función de pérdida
  `circular_loss`, la arquitectura del modelo y los umbrales de
  cizalladura que se usan en producción.
