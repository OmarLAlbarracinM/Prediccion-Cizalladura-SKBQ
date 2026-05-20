# models/ — Artefactos del Modelo de Machine Learning

## Descripción

Carpeta canónica para los artefactos entrenados del modelo LSTM de
predicción de viento. Contiene el modelo serializado y los scalers
de normalización necesarios para la inferencia.

## Contenido

```
models/
├── best_model_20h.h5    # Modelo LSTM entrenado (Keras HDF5)
├── scaler_X.pkl         # StandardScaler para las 5 features de entrada
└── scaler_y.pkl         # StandardScaler para las 3 variables objetivo
```

## Archivos

### `best_model_20h.h5` — Modelo LSTM

Modelo de red neuronal recurrente LSTM entrenado con Keras/TensorFlow.

| Propiedad | Valor |
|-----------|-------|
| **Arquitectura** | LSTM multi-salida |
| **Input shape** | `(20, 5)` — 20 timesteps × 5 features |
| **Output shape** | `(3,)` — 3 targets por timestep |
| **Features de entrada** | `dir_sin`, `dir_cos`, `intensidad_kt`, `temperatura`, `rocio` |
| **Targets de salida** | `dir_sin`, `dir_cos`, `intensidad_kt` |
| **Ventana histórica** | 20 horas (`N_BACK = 20`) |
| **Horizonte de predicción** | 1-12 horas (autoregresivo, default 6) |
| **Función de pérdida** | `circular_loss` personalizada |
| **Dataset de entrenamiento** | Reportes METAR de SKBO 2013-2024 |

#### Función de pérdida `circular_loss`

La dirección del viento se representa como componentes seno y coseno para
evitar la discontinuidad en 0°/360°. La función de pérdida pondera el
error en las componentes direccionales 3× más que el error en intensidad:

```
loss = mean(3.0 × (error_sin² + error_cos²) + error_intensidad²)
```

Esto prioriza la precisión direccional, que es el parámetro más crítico
para la detección de cizalladura.

#### Inferencia autoregresiva

El modelo predice un solo paso temporal a la vez. Para generar un
pronóstico a N horas, se usa un esquema autoregresivo:

1. Se toma la ventana de 20 horas más reciente.
2. El modelo predice `(dir_sin, dir_cos, intensidad_kt)` para H+1.
3. La predicción se concatena con las variables exógenas (temperatura,
   rocío) para formar un timestep completo de 5 features.
4. Se desliza la ventana: se descarta el timestep más antiguo y se
   agrega el predicho.
5. Se repite desde el paso 2 para H+2, H+3, etc.

### `scaler_X.pkl` — Scaler de features de entrada

`StandardScaler` de scikit-learn entrenado con `fit_transform` sobre las
5 columnas de entrada del dataset histórico completo. Normaliza los datos
a media 0 y desviación estándar 1.

| Feature | Descripción |
|---------|-------------|
| `dir_sin` | Componente seno de la dirección del viento |
| `dir_cos` | Componente coseno de la dirección del viento |
| `intensidad_kt` | Velocidad del viento en nudos |
| `temperatura` | Temperatura en °C |
| `rocio` | Punto de rocío en °C |

### `scaler_y.pkl` — Scaler de variables objetivo

`StandardScaler` entrenado sobre las 3 columnas que el modelo predice.
Se usa para desescalar las predicciones a valores físicos (inversión de
la normalización).

| Target | Descripción |
|--------|-------------|
| `dir_sin` | Componente seno predicha |
| `dir_cos` | Componente coseno predicha |
| `intensidad_kt` | Velocidad del viento predicha en nudos |

## Infraestructura

### Cómo se cargan en la API

La clase `ModelManager` en `app/model.py` carga estos tres archivos
durante el evento `lifespan` del servidor FastAPI:

```python
# app/model.py (simplificado)
_MODEL_PATH = Path(os.getenv("MODEL_PATH", "models/best_model_20h.h5"))
_SCALER_X_PATH = Path("models/scaler_X.pkl")
_SCALER_Y_PATH = Path("models/scaler_y.pkl")
```

- **`MODEL_PATH`** es configurable via variable de entorno para
  flexibilidad en diferentes entornos de despliegue.
- **Los scalers** tienen ruta fija dentro del código. Si necesitas
  cambiarlos, debes reemplazar los archivos `.pkl` en esta carpeta.

### Cómo se cargan en los pipelines

El pipeline `prediccion_lstm.py` busca los scalers en `models/` como
primera opción, con fallback a la carpeta del CSV de entrada:

```python
ruta_scaler_x = Path("models") / "scaler_X.pkl"
```

### Regeneración de scalers

Si necesitas regenerar los scalers (por ejemplo, tras agregar datos
nuevos al dataset de entrenamiento):

```bash
python pipelines/preparar_datos_lstm.py \
    --input data/Processed/skbo_ventana.csv \
    --output data/Processed/skbo_ventana_transformada.csv
# (sin --scalers = modo fit → genera nuevos scalers en models/)
```

### Despliegue Docker

El `Dockerfile` copia toda la carpeta `models/` al contenedor:

```dockerfile
COPY . .                          # incluye models/
ENV MODEL_PATH=models/best_model_20h.h5
```

Esto asegura que el modelo y los scalers estén disponibles dentro del
contenedor sin necesidad de montajes de volumen.

## Historial

| Versión | Archivo | Descripción |
|---------|---------|-------------|
| v1 | `best_model_20h.h5` | Modelo final LSTM con ventana de 20h y `circular_loss`. Entrenado en `08_prueba_lstm_pred_cizalladura.ipynb`. |

> **Nota:** Los archivos `lstm_model.h5`, `lstm_model.keras` y
> `lstm_model.pkl` fueron eliminados durante la limpieza del
> repositorio por no ser referenciados por ningún pipeline activo.
