# SKBO Wind Prediction API

API REST para prediccion de viento y deteccion de cizalladura en el Aeropuerto El Dorado (SKBO), Bogota. Desarrollada por el Grupo 7 del programa de Maestria en Inteligencia Analitica de Datos (MIAD) para la Direccion de Navegacion Aerea (DINAV) de la Fuerza Aeroespacial Colombiana.

---

## 1. Que es y que hace

La API recibe una solicitud HTTP y devuelve un pronostico de viento hora a hora para las proximas N horas (por defecto 6). Internamente descarga en tiempo real los reportes METAR mas recientes de SKBO desde la API publica de SIMFAC (Fuerza Aeroespacial Colombiana), los procesa con el mismo pipeline usado durante el entrenamiento y los pasa a un modelo LSTM entrenado con series historicas 2013-2024.

Cada prediccion entrega:
- Direccion del viento en grados meteorologicos (0-360)
- Velocidad del viento en nudos
- Rafaga maxima predicha en el horizonte
- Alerta de cizalladura hora a hora con descripcion de la causa (cambio de direccion, cambio de velocidad, o ambas)

**Ventajas**
- Sin instalacion para el usuario final: el servicio esta disponible publicamente con solo acceso a internet
- Datos en tiempo real: descarga automaticamente los METAR mas recientes en cada consulta
- Documentacion interactiva integrada: el Swagger en `/docs` permite probar el endpoint desde el navegador sin escribir codigo
- Reproducible: el Dockerfile permite levantar una copia identica del servicio en cualquier maquina con Docker

**Limitaciones**
- El modelo fue entrenado exclusivamente con datos de SKBO; no produce predicciones confiables para otros aeropuertos sin reentrenamiento
- El horizonte maximo es 12 horas; la precision disminuye a partir de H+4 por la naturaleza autoregresiva del modelo
- La velocidad predicha puede subestimarse en eventos de viento fuerte (>20 kt) ya que son infrecuentes en el conjunto de entrenamiento
- Si se envian METAR propios, se requieren minimo 20 registros horarios consecutivos para alimentar la ventana del modelo

**Advertencias**
- Esta herramienta es un apoyo a la decision operacional, no un sustituto de los sistemas certificados de la DINAV
- La disponibilidad del servicio depende de la API de SIMFAC; si SIMFAC no responde, el endpoint retorna HTTP 503
- El servicio publico corre en el plan gratuito de Render y puede tardar hasta 50 segundos en responder tras un periodo de inactividad superior a 15 minutos

---

## 2. Puesta en funcionamiento

### Opcion A: Acceso directo al servicio publico (recomendada)

No requiere descarga, instalacion ni configuracion. El servicio ya esta desplegado y disponible.

| Recurso | URL |
|---|---|
| Prediccion | `POST https://skbo-wind-api.onrender.com/predict` |
| Estado | `GET https://skbo-wind-api.onrender.com/health` |
| Documentacion interactiva | `https://skbo-wind-api.onrender.com/docs` |

**Conocimientos requeridos:** ninguno tecnico especial. Cualquier herramienta capaz de hacer solicitudes HTTP (navegador, Postman, curl, Python requests) es suficiente.

---

### Opcion B: Deploy propio con Docker

Usar esta opcion si se requiere correr el servicio en infraestructura propia o en un entorno sin acceso a internet externo.

**Conocimientos requeridos:** uso basico de la terminal, Git y Docker Desktop.

**Requisitos previos**
- Docker Desktop instalado ([descargar aqui](https://www.docker.com/products/docker-desktop/))
- Git instalado

#### Instalacion

**1. Descargar el repositorio**

```bash
git clone https://github.com/OmarLAlbarracinM/Prediccion-Cizalladura-SKBQ.git
cd Prediccion-Cizalladura-SKBQ
git checkout api
```

**2. Construir y levantar el contenedor**

```bash
docker compose up --build
```

El primer build descarga e instala TensorFlow y puede tardar entre 5 y 15 minutos. Los builds siguientes usan cache y son inmediatos.

**3. Verificar que el servicio esta activo**

```bash
curl http://localhost:8000/health
```

Respuesta esperada:
```json
{"status": "ok", "model": "loaded", "airport": "SKBO", "model_version": "lstm_v1_skbo_20h"}
```

**4. Detener el servicio**

```bash
docker compose down
```

#### Actualizacion

Cuando se publique una nueva version en el branch `api` del repositorio:

```bash
git pull origin api
docker compose up --build
```

El flag `--build` reconstruye la imagen con los cambios descargados. Si solo cambia el codigo (no las dependencias), el rebuild usa la capa de cache de pip y tarda menos de un minuto.

---

## 3. Casos de uso y paso a paso

### Caso 1: Consultar el pronostico actual (uso normal)

Paso a paso:
1. Confirmar que el servicio esta activo con `GET /health`
2. Enviar `POST /predict` con `{"horizon_hours": 6}`
3. Leer el campo `windshear_alert` para la alerta general y el arreglo `forecast` para el detalle hora a hora
4. Si `windshear_alert` es `true`, revisar `windshear_cause` en cada hora para identificar el tipo de evento

```bash
# Paso 1: verificar estado
curl https://skbo-wind-api.onrender.com/health

# Paso 2: obtener prediccion a 6 horas
curl -X POST https://skbo-wind-api.onrender.com/predict \
  -H "Content-Type: application/json" \
  -d '{"horizon_hours": 6}'
```

Respuesta esperada:
```json
{
  "airport": "SKBO",
  "prediction_horizon_hours": 6,
  "wind_direction_deg": 135.0,
  "wind_speed_kt": 4.2,
  "wind_gust_kt": 5.1,
  "windshear_alert": true,
  "forecast": [
    {"step": "H+01", "wind_direction_deg": 135.0, "wind_speed_kt": 4.2, "windshear": null,  "windshear_cause": "--"},
    {"step": "H+02", "wind_direction_deg": 165.0, "wind_speed_kt": 4.5, "windshear": true,  "windshear_cause": "dir 30.0"},
    {"step": "H+03", "wind_direction_deg": 170.0, "wind_speed_kt": 4.3, "windshear": false, "windshear_cause": "ninguna"},
    {"step": "H+04", "wind_direction_deg": 168.0, "wind_speed_kt": 4.1, "windshear": false, "windshear_cause": "ninguna"},
    {"step": "H+05", "wind_direction_deg": 172.0, "wind_speed_kt": 4.4, "windshear": false, "windshear_cause": "ninguna"},
    {"step": "H+06", "wind_direction_deg": 210.0, "wind_speed_kt": 3.9, "windshear": true,  "windshear_cause": "dir 38.0"}
  ],
  "generated_at": "2026-05-19T02:00:00Z",
  "model_version": "lstm_v1_skbo_20h",
  "data_source": "simfac_api"
}
```

### Caso 2: Consultar el pronostico desde el navegador (sin codigo)

Paso a paso:
1. Abrir `https://skbo-wind-api.onrender.com/docs` en cualquier navegador
2. Expandir la seccion `POST /predict`
3. Hacer clic en **Try it out**
4. En el dropdown de ejemplos seleccionar **"Descarga automatica desde SIMFAC (recomendado)"**
5. Hacer clic en **Execute**
6. Leer la respuesta en la seccion **Server response** debajo del boton

### Caso 3: Enviar observaciones METAR propias

Usar este caso cuando se dispone de datos propios y no se quiere depender de SIMFAC. Se requieren minimo 20 registros horarios consecutivos.

Paso a paso:
1. Preparar la lista de strings METAR en orden cronologico (del mas antiguo al mas reciente)
2. Enviar la lista en el campo `metar_observations`
3. Leer la respuesta normalmente; el campo `data_source` indicara `"provided"`

```bash
curl -X POST https://skbo-wind-api.onrender.com/predict \
  -H "Content-Type: application/json" \
  -d '{
    "metar_observations": [
      "SKBO 190000Z 13005KT 9999 FEW020 14/10 Q1025",
      "SKBO 182300Z 12004KT 9999 FEW020 15/11 Q1025",
      "... (minimo 20 registros horarios consecutivos)"
    ],
    "horizon_hours": 6
  }'
```

---

## 4. Reporte tecnico de experimentos (pruebas de la API)

El repositorio incluye un conjunto de pruebas automatizadas en `tests/test_predict.py` que validan el comportamiento funcional de los endpoints. Las pruebas se ejecutan contra el servicio publico desplegado, lo que equivale a una prueba de integracion end-to-end que cubre el stack completo: red, servidor, modelo y respuesta JSON.

### Pruebas implementadas

| Prueba | Descripcion | Resultado esperado |
|---|---|---|
| `test_health_retorna_200` | El endpoint `/health` responde | HTTP 200 |
| `test_health_modelo_cargado` | El modelo esta cargado en memoria | `status: ok`, `model: loaded` |
| `test_health_contiene_campos_requeridos` | La respuesta tiene todos los campos del contrato | Todos los campos presentes |
| `test_predict_sin_body_retorna_200` | `/predict` funciona sin body | HTTP 200 |
| `test_predict_contiene_campos_requeridos` | La respuesta cumple el contrato de la API | Todos los campos presentes |
| `test_predict_horizonte_por_defecto_es_6` | El horizonte por defecto es 6 horas | 6 pasos en `forecast` |
| `test_predict_horizonte_personalizado` | Se puede pedir un horizonte distinto | N pasos en `forecast` |
| `test_predict_direccion_en_rango_valido` | La direccion predicha es fisicamente posible | 0 <= direccion < 360 en cada hora |
| `test_predict_velocidad_no_negativa` | La velocidad predicha es fisicamente posible | velocidad >= 0 en cada hora |
| `test_predict_forecast_tiene_estructura_correcta` | Cada hora del forecast tiene todos sus campos | Estructura completa en cada paso |
| `test_predict_fuente_de_datos_es_simfac` | Sin body, los datos vienen de SIMFAC | `data_source: simfac_api` |
| `test_predict_body_invalido_retorna_400_o_422` | Parametros fuera de rango son rechazados | HTTP 400 o 422 |
| `test_predict_metar_insuficientes_retorna_400` | Menos de 20 METAR propios son rechazados | HTTP 400 |

### Como ejecutar las pruebas

```bash
pip install pytest httpx
pytest tests/test_predict.py -v
```

Para apuntar a una instancia local (deploy con Docker):

```bash
# Editar BASE_URL en tests/test_predict.py:
# BASE_URL = "http://localhost:8000"
pytest tests/test_predict.py -v
```

---

## Endpoints

| Metodo | Ruta | Descripcion |
|---|---|---|
| GET | `/health` | Estado del servicio y del modelo |
| POST | `/predict` | Genera prediccion de viento a N horas |
| GET | `/docs` | Documentacion interactiva (Swagger UI) |

---

## Variables de entorno

Copiar `.env.example` a `.env` para personalizar la configuracion antes de levantar el contenedor.

| Variable | Valor por defecto | Descripcion |
|---|---|---|
| `AIRPORT_CODE` | `SKBO` | Codigo OACI del aeropuerto |
| `MODEL_PATH` | `docs/notebooks/best_model_20h.h5` | Ruta al modelo entrenado |
| `PORT` | `8000` | Puerto de escucha del servidor |
| `LOG_LEVEL` | `info` | Nivel de log (`debug`, `info`, `warning`) |

---

## Estructura del repositorio

```
Prediccion-Cizalladura-SKBQ/  (branch: api)
├── app/
│   ├── main.py            # Entrypoint FastAPI
│   ├── model.py           # Carga del modelo e inferencia
│   ├── preprocessing.py   # Pipeline de features desde METAR
│   └── schemas.py         # Modelos Pydantic request/response
├── docs/notebooks/
│   ├── best_model_20h.h5  # Modelo LSTM entrenado
│   └── Prueba_LSTM_pred_cizalladura.ipynb
├── models/
│   ├── scaler_X.pkl       # Scaler de features de entrada
│   └── scaler_y.pkl       # Scaler de salida del modelo
├── tests/
│   └── test_predict.py    # Pruebas automatizadas de los endpoints
├── pipelines/             # Scripts del pipeline de datos
├── Dockerfile
├── docker-compose.yml
├── render.yaml
├── requirements.txt
└── .env.example
```

---

## Integrantes

Este artefacto fue desarrollado como parte del Proyecto Aplicado en Analítica de Datos del Grupo 7, conformado por Tatiana García, Edwin Ramírez, Omar Albarracín y Joaquín Abondano​.
