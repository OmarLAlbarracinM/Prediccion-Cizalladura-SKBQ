# tests/ — Pruebas Automatizadas

## Descripción

Suite de pruebas de integración que validan el correcto funcionamiento
de la API de predicción de viento en producción. Las pruebas verifican
disponibilidad del servicio, carga del modelo, estructura del contrato
JSON, validez física de las predicciones y manejo de errores.

## Estructura

```
tests/
└── test_predict.py    # Pruebas de integración contra la API desplegada
```

## `test_predict.py`

### Qué prueba y por qué

El archivo contiene dos clases de pruebas que cubren los dos endpoints
de la API:

#### `TestHealth` — Endpoint `/health`

| Test | Qué verifica | Por qué es importante |
|------|-------------|----------------------|
| `test_health_retorna_200` | El endpoint responde HTTP 200. | Confirma que el servidor está activo y accesible en la red. |
| `test_health_modelo_cargado` | El campo `model` es `"loaded"`. | Si el modelo no cargó durante el startup, las predicciones fallarán. |
| `test_health_contiene_campos_requeridos` | Presencia de `status`, `model`, `airport`, `model_version`. | Garantiza que clientes que dependen de estos campos no recibirán respuestas incompletas. |

#### `TestPredict` — Endpoint `/predict`

| Test | Qué verifica | Por qué es importante |
|------|-------------|----------------------|
| `test_predict_sin_body_retorna_200` | `POST /predict` con `{}` retorna 200. | Valida el modo automático (descarga desde SIMFAC). |
| `test_predict_contiene_campos_requeridos` | Presencia de los 10 campos del contrato (`airport`, `forecast`, etc.). | Cualquier campo faltante rompe la integración con sistemas consumidores. |
| `test_predict_horizonte_por_defecto_es_6` | Sin `horizon_hours`, el forecast tiene 6 pasos. | Confirma el horizonte operacional por defecto para la DINAV. |
| `test_predict_horizonte_personalizado` | Con `horizon_hours: 3`, el forecast tiene 3 pasos. | Valida que los clientes pueden ajustar el horizonte. |
| `test_predict_direccion_en_rango_valido` | Dirección en cada hora está en `[0°, 360°)`. | Una dirección fuera de rango indica error en la conversión seno/coseno → grados. |
| `test_predict_velocidad_no_negativa` | Velocidad en cada hora es `≥ 0`. | Velocidad negativa indica error en el desescalado del modelo. |
| `test_predict_forecast_tiene_estructura_correcta` | Cada hora tiene `step`, `wind_direction_deg`, `wind_speed_kt`, `windshear`, `windshear_cause`. | Un campo faltante rompe la lectura del pronóstico. |
| `test_predict_fuente_de_datos_es_simfac` | `data_source` es `"simfac_api"` sin METAR propios. | Confirma que el modo automático funciona. |
| `test_predict_body_invalido_retorna_400_o_422` | `horizon_hours: 99` retorna 400 o 422. | Valida la protección contra parámetros inválidos. |
| `test_predict_metar_insuficientes_retorna_400` | Un solo METAR retorna 400. | El modelo requiere mínimo 20 registros horarios. |

### Infraestructura de pruebas

**Entorno de ejecución:** por defecto las pruebas apuntan al servicio
público desplegado en Render:

```python
BASE_URL = "https://skbo-wind-api.onrender.com"
TIMEOUT = 120  # segundos (la primera llamada puede tardar por cold start)
```

**Para pruebas locales:** cambiar `BASE_URL` a `http://localhost:8000`
y levantar el servicio con Docker Compose:

```bash
docker compose up --build -d
```

**Dependencias de pruebas:**

```bash
pip install pytest httpx
```

> **Nota:** `httpx` se usa en lugar de `requests` porque es más moderno
> y soporta HTTP/2. No está en `requirements.txt` porque no es
> dependencia de la API, solo de las pruebas.

## Ejecución

```bash
# Ejecutar todas las pruebas
pytest tests/test_predict.py -v

# Ejecutar solo pruebas de health
pytest tests/test_predict.py::TestHealth -v

# Ejecutar solo pruebas de predict
pytest tests/test_predict.py::TestPredict -v

# Ejecutar una prueba específica
pytest tests/test_predict.py::TestPredict::test_predict_direccion_en_rango_valido -v
```

## Tiempos esperados

| Escenario | Tiempo aprox. |
|-----------|--------------|
| Primera ejecución contra Render (cold start) | 60-120 seg |
| Ejecuciones posteriores contra Render | 5-15 seg |
| Contra instancia local (`localhost:8000`) | 2-5 seg |

> **Cold start en Render:** el plan gratuito suspende el servicio
> después de 15 minutos de inactividad. La primera petición reactiva
> el contenedor, lo que puede tardar hasta 2 minutos.

## Cobertura

Las pruebas actuales son de **integración end-to-end**: llaman a la API
completa con conexión real a SIMFAC. No hay pruebas unitarias aisladas
del modelo o del preprocesamiento.

### Posibles mejoras futuras

- Pruebas unitarias para `preprocessing.py` con datos METAR fijos.
- Pruebas unitarias para `ModelManager` con un modelo mock.
- Pruebas de regresión que comparen las predicciones contra un baseline
  conocido.
- Tests parametrizados para distintos códigos OACI.
