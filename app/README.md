# app/ — API FastAPI de Predicción de Viento

## Descripción

Esta carpeta contiene el **servicio web de producción** construido con
[FastAPI](https://fastapi.tiangolo.com/). La API expone un modelo LSTM
que predice dirección, velocidad del viento y alertas de cizalladura
para el Aeropuerto Internacional El Dorado (SKBO), Bogotá.

## Arquitectura

```
app/
├── __init__.py          # Marca el directorio como paquete Python
├── main.py              # Definición de la aplicación FastAPI, endpoints y lifespan
├── model.py             # ModelManager: carga del modelo, inferencia autoregresiva
├── preprocessing.py     # Pipeline de preprocesamiento al vuelo (METAR → features)
└── schemas.py           # Esquemas Pydantic para request/response
```

## Endpoints

| Método   | Ruta       | Descripción                                                                         |
| -------- | ---------- | ----------------------------------------------------------------------------------- |
| `GET`/`HEAD` | `/health`  | Health check. Confirma que el servidor y el modelo están operativos.              |
| `POST`   | `/predict` | Genera un pronóstico de viento a N horas. Acepta body vacío o con observaciones METAR propias. |

### `POST /predict`

**Modo automático (recomendado):** enviar un body vacío `{}`. La API
descarga automáticamente los últimos reportes METAR desde la API de
SIMFAC (Fuerza Aérea Colombiana) y genera el pronóstico.

**Modo manual:** enviar un array de strings METAR en el campo
`metar_observations` (mínimo 20 registros horarios consecutivos).

## Módulos

### `main.py`

Punto de entrada de la aplicación. Define:

- **Lifespan event:** carga el modelo LSTM y los scalers al iniciar el
  servidor (antes de aceptar peticiones).
- **`/health`:** retorna el estado del modelo, el código de aeropuerto y
  la versión del modelo.
- **`/predict`:** orquesta preprocesamiento → inferencia → respuesta JSON
  con el pronóstico hora a hora y la alerta de cizalladura global.

### `model.py`

Clase `ModelManager` que encapsula:

- **Carga del modelo:** lee `best_model_20h.h5` desde la ruta definida en
  la variable de entorno `MODEL_PATH` (default: `models/best_model_20h.h5`).
  Registra la función de pérdida personalizada `circular_loss` para
  poder deserializar el archivo `.h5`.
- **Carga de scalers:** lee `scaler_X.pkl` y `scaler_y.pkl` desde `models/`.
  Estos son `StandardScaler` de scikit-learn entrenados sobre el dataset
  histórico completo (2013-2024).
- **Inferencia autoregresiva:** dado un DataFrame con al menos 20 horas
  de historia, predice iterativamente las próximas N horas. En cada paso,
  la predicción del modelo se concatena con las variables exógenas
  (temperatura y punto de rocío) y se desliza la ventana temporal.
- **Conversión física:** transforma las componentes seno/coseno de la
  dirección predicha a grados meteorológicos `[0°, 360°)` y recorta
  intensidades negativas.
- **Análisis de cizalladura:** compara dirección e intensidad entre horas
  consecutivas. Si la diferencia angular supera 30° o la diferencia de
  velocidad supera 10 kt, se genera una alerta.

### `preprocessing.py`

Pipeline de preprocesamiento en tiempo real. Réplica las transformaciones
del pipeline `preparar_datos_lstm.py`, pero diseñado para inferencia
(usa `transform`, no `fit_transform`).

Funcionalidades:

- **Descarga desde SIMFAC:** consulta la API pública del SIMFAC para
  obtener las últimas 30 horas de reportes METAR del aeropuerto
  configurado.
- **Parsing de METAR:** extrae dirección del viento, velocidad, ráfaga,
  temperatura y punto de rocío usando expresiones regulares.
- **Transformación circular:** convierte la dirección del viento en
  componentes seno y coseno para evitar la discontinuidad en 0°/360°.
- **Resampleo horario e interpolación:** agrega los datos a frecuencia
  horaria y rellena gaps con interpolación lineal.
- **Escalado:** aplica el `scaler_X` pre-entrenado (solo `transform`,
  nunca `fit`).

### `schemas.py`

Esquemas Pydantic v2 que definen los contratos de la API:

| Esquema           | Uso                                         |
| ----------------- | ------------------------------------------- |
| `PredictRequest`  | Body del `POST /predict`. Campos opcionales `metar_observations` y `horizon_hours`. |
| `HourForecast`    | Un paso del pronóstico (dirección, velocidad, cizalladura, causa). |
| `PredictResponse` | Respuesta completa: aeropuerto, horizonte, alerta global, forecast y metadatos. |
| `HealthResponse`  | Respuesta de `/health`: status, modelo, aeropuerto, versión. |

## Infraestructura

La API se despliega como un contenedor Docker. La cadena de configuración es:

```
.env / .env.example          Variables de entorno para desarrollo local
        │
        ▼
  docker-compose.yml          Orquestación local (docker compose up)
        │
        ▼
    Dockerfile                Imagen basada en python:3.11-slim
        │
        ▼
  render.yaml / railway.toml  Configuración de despliegue en la nube
```

### Variables de entorno

| Variable       | Descripción                                         | Default                        |
| -------------- | --------------------------------------------------- | ------------------------------ |
| `AIRPORT_CODE` | Código OACI del aeropuerto                          | `SKBO`                         |
| `MODEL_PATH`   | Ruta al archivo `.h5` del modelo entrenado          | `models/best_model_20h.h5`    |
| `PORT`         | Puerto HTTP del servidor                            | `8000`                         |
| `LOG_LEVEL`    | Nivel de logging de Uvicorn (`info`, `debug`, etc.) | `info`                         |

### Despliegue en Render

El servicio se despliega en [Render](https://render.com/) usando la
configuración en `render.yaml`. Al hacer push a la rama `api`, Render
reconstruye la imagen Docker automáticamente. El health check en `/health`
verifica que el modelo esté cargado antes de enrutar tráfico.

### Ejecución local

```bash
# Con Docker Compose
docker compose up --build

# Sin Docker (desarrollo)
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Dependencias

Definidas en `requirements.txt` en la raíz del proyecto:

- **FastAPI + Uvicorn:** framework web asíncrono y servidor ASGI.
- **Pydantic:** validación de datos y serialización JSON.
- **TensorFlow:** carga y ejecución del modelo LSTM.
- **pandas + NumPy:** manipulación de datos tabulares.
- **scikit-learn + joblib:** carga de scalers pre-entrenados.
