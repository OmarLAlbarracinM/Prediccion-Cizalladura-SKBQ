# Sistema Predictivo de Cizalladura del Viento — Aeropuerto El Dorado (SKBO)

**Documento de Contextualización**
*Maestría en Inteligencia Analítica de Datos*

---

Este documento presenta una visión integral del proyecto de grado orientado a la **predicción de cizalladura del viento** en el Aeropuerto Internacional El Dorado (SKBO), Bogotá, Colombia. Está estructurado en dos bloques complementarios:

- **Bloque 1 — Perspectiva de Negocio:** explica el problema, el contexto operacional, la propuesta de valor y el impacto real del proyecto. Está escrito para que cualquier persona, independientemente de su formación técnica, pueda comprender qué hace el sistema, para qué sirve y por qué es importante.
- **Bloque 2 — Perspectiva Técnica:** detalla la arquitectura de datos, el modelado matemático, la infraestructura de software y el ciclo de vida completo del sistema. Está dirigido a perfiles con conocimiento en ciencia de datos, ingeniería de software o meteorología operacional.

---

# BLOQUE 1: Perspectiva de Negocio e Impacto Operacional

## 1.1 El Problema: La Cizalladura del Viento en la Aviación

La **cizalladura del viento** (*windshear*) es un cambio repentino y significativo en la velocidad o la dirección del viento que ocurre en una distancia muy corta, tanto horizontal como verticalmente. Este fenómeno meteorológico es reconocido por la Organización de Aviación Civil Internacional (OACI) como uno de los peligros más críticos para la aviación, especialmente durante las fases de **despegue** y **aterrizaje**, cuando las aeronaves vuelan a baja velocidad y baja altitud.

Cuando un avión se encuentra con cizalladura durante el aterrizaje, puede experimentar:
- **Pérdida súbita de sustentación:** si el viento de frente disminuye bruscamente, el avión pierde velocidad aerodinámica y puede descender por debajo de la senda de aproximación.
- **Desviación lateral:** si la dirección del viento cambia drásticamente (por ejemplo, de 130° a 200°), el piloto debe corregir rápidamente la trayectoria, lo cual en condiciones de baja visibilidad o turbulencia puede ser extremadamente peligroso.
- **Frustración del aterrizaje (*go-around*):** los pilotos están entrenados para abortar el aterrizaje si detectan cizalladura, lo que implica consumo adicional de combustible, retrasos en cadena para otros vuelos y saturación del espacio aéreo.

### ¿Por qué El Dorado (SKBO)?

El Aeropuerto Internacional El Dorado está ubicado en la sabana de Bogotá, a **2.547 metros sobre el nivel del mar** (uno de los aeropuertos más altos del mundo con tráfico comercial internacional). Esta ubicación geográfica presenta condiciones particulares:

- **Topografía circundante:** la sabana está rodeada por cerros al oriente y terreno plano al occidente, lo que canaliza corrientes de aire y genera cambios de dirección abruptos.
- **Variabilidad térmica diurna:** la diferencia de temperatura entre el amanecer y las primeras horas de la tarde puede superar los 15°C, generando brisas convectivas que alteran el régimen de vientos.
- **Alta densidad de tráfico aéreo:** El Dorado es el aeropuerto con más movimiento de carga aérea en Latinoamérica y uno de los de mayor tráfico de pasajeros, lo que hace que cualquier incidente meteorológico tenga un impacto operacional amplificado.

### ¿Cómo se maneja hoy?

Actualmente, la detección de cizalladura en El Dorado opera de forma **reactiva**:

1. Un piloto experimenta cizalladura durante el aterrizaje o despegue.
2. El piloto reporta la condición al controlador de tráfico aéreo (ATC) por radio.
3. El ATC informa a las aeronaves subsiguientes y, si es severo, puede cerrar temporalmente la pista afectada.

Este ciclo deja un **margen de reacción muy corto**: la alerta llega *después* de que la primera aeronave ya fue afectada. No existe un mecanismo automatizado que anticipe la cizalladura con horas de anticipación basándose en datos meteorológicos objetivos.

## 1.2 La Solución: Un Sistema Predictivo Basado en Inteligencia Artificial

Este proyecto transforma el enfoque de **reactivo** a **predictivo**. Hemos construido un sistema de Inteligencia Artificial que:

1. **Lee automáticamente** el estado actual del clima del aeropuerto: dirección del viento, velocidad, ráfagas, temperatura y punto de rocío. Esta información se descarga directamente del Sistema de Información Meteorológica de la Fuerza Aérea Colombiana (SIMFAC), sin intervención humana.

2. **Analiza el historial reciente:** toma las últimas 20 horas de datos meteorológicos horarios y detecta patrones de cambio que históricamente han precedido a eventos de cizalladura.

3. **Predice el futuro:** genera un pronóstico hora a hora para las **próximas 6 horas**, indicando para cada hora:
   - La dirección esperada del viento (en grados, de 0° a 360°).
   - La velocidad esperada del viento (en nudos).
   - Si habrá cizalladura o no (Sí / No).
   - La causa específica: cambio de dirección (ej. "Δ35.2°"), cambio de velocidad (ej. "Δ12.4 kt"), o ambas.

4. **Emite una alerta global:** si en cualquiera de las 6 horas pronosticadas el sistema detecta que la dirección cambiará más de **30 grados** o la velocidad cambiará más de **10 nudos** entre horas consecutivas, genera automáticamente una **Alerta de Cizalladura**.

### Ejemplo real de salida del sistema

Cuando se consulta la API del sistema, se obtiene una respuesta como la siguiente:

```
Hora        Dirección   Velocidad   Cizalladura   Causa
────────────────────────────────────────────────────────
H+01            132.4        5.3          --          --
H+02            150.6        4.1        No        ninguna
H+03            183.2        4.5        Sí      dir Δ32.6°
H+04            187.4        4.3        No        ninguna
H+05            186.2        4.6        No        ninguna
H+06            180.5        3.8        No        ninguna
────────────────────────────────────────────────────────
⚠ ALERTA GLOBAL DE CIZALLADURA: Sí (detectada en H+03)
```

En este ejemplo, el sistema detectó con **3 horas de anticipación** que el viento cambiaría de dirección más de 30°, permitiendo al controlador de tráfico tomar decisiones preventivas.

## 1.3 Propuesta de Valor

| Dimensión | Situación Actual (Reactiva) | Con este Sistema (Predictiva) |
|---|---|---|
| **Tiempo de alerta** | Después de que un piloto la experimenta | Hasta 6 horas de anticipación |
| **Automatización** | Depende del reporte verbal del piloto | 100% automatizado, sin intervención humana |
| **Disponibilidad** | Solo cuando hay un vuelo que la reporte | 24/7, independiente del tráfico aéreo |
| **Precisión** | Subjetiva (percepción del piloto) | Objetiva (basada en datos numéricos) |
| **Fuente de datos** | Experiencia individual | +10 años de datos históricos analizados por IA |

### Beneficiarios directos

- **Controladores de tráfico aéreo (ATC):** pueden ajustar la separación entre aeronaves, asignar pistas favorables o emitir NOTAM (Notificaciones al Aeropuerto) con horas de anticipación.
- **Meteorólogos de la Fuerza Aérea (SIMFAC):** disponen de un instrumento cuantitativo que complementa sus pronósticos de área y terminal.
- **Aerolíneas y operadores:** pueden planificar el consumo de combustible, anticipar posibles go-arounds y optimizar la programación de vuelos.
- **Pasajeros:** se reduce el riesgo de incidentes relacionados con cizalladura y se minimizan los retrasos operacionales derivados.

---

# BLOQUE 2: Perspectiva Técnica y de Arquitectura

## 2.1 Visión General del Sistema

El proyecto implementa un pipeline de Machine Learning de extremo a extremo (*end-to-end*) que abarca desde la adquisición de datos meteorológicos en tiempo real hasta la entrega de predicciones a través de una API REST desplegada en la nube. La arquitectura sigue principios de **MLOps** (Machine Learning Operations) para garantizar reproducibilidad, escalabilidad y mantenibilidad.

```
┌────────────────────────────────────────────────────────────────────────────┐
│                       ARQUITECTURA DEL SISTEMA                            │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌──────────────┐    ┌──────────────────┐    ┌───────────────────────┐     │
│  │  API SIMFAC   │───▶│  Preprocesamiento │───▶│  Modelo LSTM         │    │
│  │  (Fuerza Aérea│    │  (Feature Eng.)   │    │  (Inferencia)        │    │
│  │  Colombiana)  │    │                    │    │                      │    │
│  └──────────────┘    └──────────────────┘    └──────────┬────────────┘    │
│                                                          │                 │
│                                               ┌──────────▼────────────┐   │
│                                               │  Análisis Cizalladura │   │
│                                               │  (Umbral 30° / 10kt) │   │
│                                               └──────────┬────────────┘   │
│                                                          │                 │
│                                               ┌──────────▼────────────┐   │
│                                               │  API REST (FastAPI)   │   │
│                                               │  JSON Response        │   │
│                                               └───────────────────────┘   │
│                                                                            │
├────────────────────────────────────────────────────────────────────────────┤
│  Infraestructura: Docker → Render (Cloud) / localhost (desarrollo)        │
└────────────────────────────────────────────────────────────────────────────┘
```

## 2.2 Datos y Pipeline de Preparación

### Fuente de datos

La fuente primaria son los reportes **METAR** (Meteorological Aerodrome Report), el estándar mundial de la OACI para reportar condiciones meteorológicas en aeropuertos. Cada reporte es una cadena de texto codificada, por ejemplo:

```
SKBO 190000Z 13005KT 9999 FEW020 14/10 Q1025
│     │        │       │     │     │     │
│     │        │       │     │     │     └─ Presión altimétrica (1025 hPa)
│     │        │       │     │     └─ Temperatura 14°C / Rocío 10°C
│     │        │       │     └─ Nubosidad: pocas nubes a 2000 ft
│     │        │       └─ Visibilidad: 10 km o más
│     │        └─ Viento: dirección 130°, velocidad 5 nudos
│     └─ Fecha y hora UTC (día 19, 00:00Z)
└─ Código OACI del aeropuerto
```

Se utilizó un **dataset histórico de más de 10 años** (2013-2024) de reportes METAR de SKBO obtenidos a través de la API pública del SIMFAC (Sistema de Información de la Fuerza Aérea Colombiana), con un total de decenas de miles de registros.

### Pipeline de preprocesamiento

Los reportes METAR crudos pasan por un pipeline automatizado de 6 etapas antes de ser consumidos por el modelo:

| Etapa | Qué hace | Por qué es necesario |
|-------|----------|---------------------|
| **1. Limpieza** | Elimina reportes `NIL` (no disponibles) y registros con fechas inválidas (año 1900). | Datos corruptos del sistema fuente contaminarían el entrenamiento. |
| **2. Tokenización** | Divide la cadena METAR en tokens y elimina la keyword `AUTO` (reporte automático que no aporta información meteorológica). | Permite la extracción posicional de variables. |
| **3. Extracción de variables** | Usa expresiones regulares y posición para extraer: dirección del viento, velocidad, ráfaga, temperatura y punto de rocío. | El modelo necesita variables numéricas, no texto. |
| **4. Transformación circular** | Convierte la dirección del viento (0° a 360°) en dos componentes: **seno** y **coseno**. | Sin esta transformación, el modelo interpretaría erróneamente que 359° y 001° están "lejos" cuando en realidad están separados solo 2°. |
| **5. Resampleo horario** | Agrega múltiples reportes de una misma hora en un solo registro promedio y rellena horas faltantes con interpolación lineal. | El modelo LSTM necesita una serie temporal estrictamente regular (un dato por hora, sin huecos). |
| **6. Normalización** | Aplica `StandardScaler` (media=0, desviación estándar=1) a las 5 variables de entrada. | Las redes neuronales convergen más rápido y con mayor precisión cuando las variables están en la misma escala. |

### Variables del modelo

| Variable | Tipo | Descripción |
|----------|------|-------------|
| `dir_sin` | Entrada | Componente seno de la dirección del viento |
| `dir_cos` | Entrada | Componente coseno de la dirección del viento |
| `intensidad_kt` | Entrada + Salida | Velocidad del viento en nudos |
| `temperatura` | Entrada (exógena) | Temperatura ambiente en °C |
| `rocio` | Entrada (exógena) | Punto de rocío en °C |

**Total:** 5 variables de entrada → 3 variables de salida (`dir_sin`, `dir_cos`, `intensidad_kt`).

## 2.3 El Modelo: Red Neuronal LSTM

### ¿Por qué LSTM?

Se evaluaron múltiples arquitecturas de redes neuronales recurrentes durante la fase de experimentación (documentada en 9 notebooks del repositorio). La arquitectura **LSTM (Long Short-Term Memory)** fue seleccionada porque:

- **Memoria a largo plazo:** las compuertas internas de la LSTM (*forget gate*, *input gate*, *output gate*) le permiten "recordar" patrones meteorológicos que se extienden a lo largo de varias horas, sin sufrir el problema de desvanecimiento de gradiente que afecta a las redes recurrentes simples (RNN).
- **Superioridad empírica:** en las pruebas comparativas (notebook `04_prueba_lstm_gru.ipynb`), la LSTM superó a la arquitectura GRU (Gated Recurrent Unit) en la predicción de dirección del viento para este caso de uso.

### Configuración del modelo

| Parámetro | Valor | Justificación |
|-----------|-------|---------------|
| **Ventana de entrada** | 20 horas | Experimentación mostró que 20h captura los ciclos diurnos de viento en SKBO sin introducir ruido de días anteriores. |
| **Horizonte de predicción** | 1-12 horas (default: 6) | 6 horas es el horizonte operacional estándar del TAF (Terminal Aerodrome Forecast) de la OACI. |
| **Forma del input** | `(20, 5)` | 20 timesteps × 5 features por timestep. |
| **Forma del output** | `(3,)` | 3 targets: `dir_sin`, `dir_cos`, `intensidad_kt`. |
| **Dataset de entrenamiento** | METAR SKBO 2013-2024 | +10 años de datos meteorológicos horarios. |

### Innovación: Función de Pérdida Circular (`circular_loss`)

El reto matemático más importante del proyecto fue la representación de la dirección del viento. La dirección es una **variable circular**: los 360° y los 0° son el mismo punto. Las funciones de pérdida estándar (MSE, MAE) penalizan erróneamente una predicción de 359° cuando el valor real es 1° (interpretarían un error de 358° cuando el error real es solo 2°).

La solución implementada tiene dos componentes:

1. **Representación trigonométrica:** se reemplaza el ángulo θ por `(sin θ, cos θ)`. Con esta representación, 359° = (sin 359°, cos 359°) ≈ (-0.017, 0.999) y 1° = (sin 1°, cos 1°) ≈ (0.017, 0.999), que están numéricamente muy cerca.

2. **Ponderación asimétrica:** la función de pérdida personalizada `circular_loss` asigna un peso **3 veces mayor** al error direccional que al error de velocidad:

```
circular_loss = mean( 3.0 × (error_sin² + error_cos²) + error_velocidad² )
```

Esto fuerza al modelo a priorizar la precisión direccional, que es el factor más determinante para la detección de cizalladura (un cambio de dirección de 30° es más peligroso que un cambio de velocidad de 5 kt).

### Inferencia Autoregresiva

El modelo predice un único paso temporal a la vez. Para generar un pronóstico a 6 horas, se utiliza un esquema **autoregresivo**:

```
Paso 1: ventana[H-20 ... H₀] → modelo → predicción H+1
Paso 2: ventana[H-19 ... H+1] → modelo → predicción H+2
Paso 3: ventana[H-18 ... H+2] → modelo → predicción H+3
...
Paso 6: ventana[H-15 ... H+5] → modelo → predicción H+6
```

En cada paso:
1. El modelo predice `(dir_sin, dir_cos, intensidad_kt)` para la siguiente hora.
2. La predicción se concatena con las variables exógenas (temperatura y rocío) para formar un timestep completo de 5 features.
3. La ventana se "desliza": se descarta el timestep más antiguo y se incorpora el recién predicho.
4. Se repite el proceso para la siguiente hora.

Las variables exógenas (temperatura y punto de rocío) se toman de los datos más recientes disponibles. Si no hay datos futuros, se aplica *forward-fill* (se asume que la última temperatura conocida se mantiene).

## 2.4 Análisis de Cizalladura

Una vez obtenidas las predicciones para las 6 horas, el sistema aplica un **análisis de cizalladura** que compara cada hora con la anterior:

| Condición | Umbral | Origen del umbral |
|-----------|--------|-------------------|
| Cambio de dirección ≥ 30° | `Δdir ≥ 30°` | Criterio operacional OACI para cizalladura lateral |
| Cambio de velocidad ≥ 10 kt | `Δvel ≥ 10 kt` | Criterio operacional para ráfagas significativas |

El cambio de dirección se calcula con ajuste circular: `min(|d₂ - d₁|, 360 - |d₂ - d₁|)` para evitar falsos positivos en el cruce del norte (0°/360°).

Si alguna hora supera al menos uno de los umbrales, el campo `windshear` se marca como `True` y el campo `windshear_cause` describe la causa específica (cambio de dirección, de velocidad, o ambos).

## 2.5 Infraestructura y Despliegue (MLOps)

### Estructura del repositorio

```
Prediccion-Cizalladura-SKBQ/
│
├── app/                        # API FastAPI (código de producción)
│   ├── main.py                 # Endpoints /health y /predict
│   ├── model.py                # ModelManager: carga, inferencia, cizalladura
│   ├── preprocessing.py        # Preprocesamiento en tiempo real
│   └── schemas.py              # Contratos Pydantic (request/response)
│
├── data/                       # Datos (versionados con DVC)
│   ├── raw/                    # METAR crudos (DATOS_CRUDOS.csv)
│   ├── Processed/              # Datos transformados y predicciones
│   └── NewData/                # Datos nuevos pendientes de ingesta
│
├── docs/                       # Investigación y experimentación
│   ├── notebooks/              # 3 notebooks del flujo principal (EDA, preprocesamiento, features)
│   └── experimentos_notebooks/ # 10 notebooks de pruebas de hipótesis y arquitecturas
│
├── models/                     # Artefactos del modelo entrenado
│   ├── best_model_20h.h5       # Modelo LSTM (Keras HDF5)
│   ├── scaler_X.pkl            # StandardScaler de entrada (5 features)
│   └── scaler_y.pkl            # StandardScaler de salida (3 targets)
│
├── pipelines/                  # Scripts automatizados de datos
│   ├── consultar_api_metar.py  # Consulta a la API SIMFAC
│   ├── ventana_metar.py        # Descarga ventana temporal
│   ├── ingestion_new_data.py   # Ingesta + versionado DVC
│   ├── preprocesamiento_metar.py  # Limpieza y extracción
│   ├── preparar_datos_lstm.py  # Feature engineering + escalado
│   └── prediccion_lstm.py      # Inferencia autoregresiva
│
├── tests/                      # Pruebas automatizadas de integración
│   └── test_predict.py         # 13 tests contra la API
│
├── Dockerfile                  # Imagen Docker (python:3.11-slim)
├── docker-compose.yml          # Orquestación local
├── render.yaml                 # Configuración de despliegue en Render
├── railway.toml                # Configuración alternativa (Railway)
├── requirements.txt            # Dependencias Python
└── .env.example                # Variables de entorno
```

### API REST (FastAPI)

El sistema expone una API web construida con **FastAPI** (framework Python asíncrono de alto rendimiento):

| Endpoint | Método | Función |
|----------|--------|---------|
| `/health` | `GET` | Verificación de salud del servidor y estado del modelo. |
| `/predict` | `POST` | Genera pronóstico de viento con análisis de cizalladura. |
| `/docs` | `GET` | Documentación interactiva Swagger/OpenAPI (auto-generada). |

El endpoint `/predict` acepta dos modos de operación:
- **Modo automático** (body vacío `{}`): la API descarga los últimos 30 reportes METAR desde SIMFAC, los procesa y genera el pronóstico. Este es el modo recomendado para uso en producción.
- **Modo manual** (array de strings METAR): el usuario envía sus propias observaciones METAR (mínimo 20 registros horarios). Útil para pruebas o para alimentar el sistema con datos de otros aeropuertos.

### Contenerización (Docker)

Todo el sistema —sistema operativo, dependencias de IA (TensorFlow 2.17, pandas, scikit-learn), el modelo entrenado y la API— está empaquetado en una imagen Docker basada en `python:3.11-slim`. Esto garantiza:

- **Reproducibilidad:** el sistema funciona exactamente igual en cualquier máquina que ejecute Docker, eliminando problemas de "en mi máquina sí funciona".
- **Aislamiento:** las dependencias no interfieren con otros proyectos del servidor.
- **Portabilidad:** la imagen puede desplegarse en cualquier proveedor de nube (AWS, GCP, Azure, Render, Railway) sin modificaciones.

### Despliegue en la nube (Render)

La API está actualmente desplegada en la plataforma **Render** con despliegue continuo:

1. El desarrollador hace `git push` al repositorio en GitHub.
2. Render detecta el cambio y reconstruye automáticamente la imagen Docker.
3. El nuevo contenedor reemplaza al anterior sin downtime.
4. El endpoint `/health` verifica que el modelo LSTM cargó correctamente antes de aceptar tráfico.

### Variables de entorno

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `AIRPORT_CODE` | Código OACI del aeropuerto | `SKBO` |
| `MODEL_PATH` | Ruta al modelo `.h5` | `models/best_model_20h.h5` |
| `PORT` | Puerto HTTP | `8000` |
| `LOG_LEVEL` | Nivel de logging | `info` |

### Versionado de datos (DVC)

Los datasets grandes (CSV con +100 mil registros) no se almacenan en Git. Se utiliza **DVC** (Data Version Control), una herramienta de versionado de datos que funciona como Git pero para archivos grandes. Los archivos `.dvc` (ligeros, de pocos bytes) se rastrean en Git y apuntan al CSV real almacenado en un backend remoto.

### Pruebas automatizadas

El proyecto incluye una suite de **13 pruebas de integración** (`pytest`) que validan:

| Categoría | Tests | Qué verifican |
|-----------|-------|---------------|
| **Disponibilidad** | 3 | Servidor activo, modelo cargado, campos de `/health` completos. |
| **Funcionalidad** | 5 | Pronóstico con horizonte default (6h) y personalizado (3h), descarga automática desde SIMFAC, estructura del forecast. |
| **Validez física** | 2 | Dirección en rango [0°, 360°), velocidad no negativa. |
| **Manejo de errores** | 3 | Horizonte inválido (99h), METAR insuficientes (<20), body malformado. |

Las pruebas se ejecutan contra el contenedor Docker local y contra el servicio en producción (Render).

## 2.6 Tecnologías Utilizadas

| Capa | Tecnología | Versión | Rol |
|------|------------|---------|-----|
| **Lenguaje** | Python | 3.11 | Lenguaje base de todo el proyecto. |
| **Deep Learning** | TensorFlow / Keras | 2.17.0 | Entrenamiento e inferencia del modelo LSTM. |
| **Datos** | pandas | 2.2.2 | Manipulación de series temporales y DataFrames. |
| **Matemáticas** | NumPy | 1.26.4 | Operaciones numéricas (trigonometría, álgebra lineal). |
| **Normalización** | scikit-learn | 1.8.0 | `StandardScaler` para normalización de features. |
| **Serialización** | joblib | 1.4.2 | Persistencia de scalers entrenados (`.pkl`). |
| **API Web** | FastAPI | 0.115.0 | Framework HTTP asíncrono de alto rendimiento. |
| **Servidor** | Uvicorn | 0.30.6 | Servidor ASGI para producción. |
| **Validación** | Pydantic | 2.7.4 | Esquemas de request/response con validación automática. |
| **Contenerización** | Docker | — | Empaquetado del sistema para despliegue. |
| **Versionado de datos** | DVC | — | Control de versiones de datasets grandes. |
| **Despliegue** | Render | — | Plataforma de hosting con CI/CD automático. |
| **Testing** | pytest + httpx | — | Suite de pruebas de integración. |

---

## Conclusión

Este proyecto no se limita a un análisis exploratorio o a un modelo predictivo aislado. Es un **sistema de software de producción** que integra:

1. **Ciencia de datos:** análisis exploratorio de +10 años de datos meteorológicos, feature engineering especializado (representación circular del viento) y evaluación rigurosa de múltiples arquitecturas de deep learning.

2. **Ingeniería de software:** API REST con documentación automática, contenerización Docker, despliegue continuo en la nube, pruebas automatizadas y versionado de datos.

3. **Impacto operacional real:** un sistema que puede integrarse a los procesos de toma de decisiones de la aviación colombiana, anticipando con horas un fenómeno que hoy solo se detecta de forma reactiva.

El código fuente completo, los notebooks de experimentación, los pipelines de datos y la API están disponibles en el repositorio GitHub del proyecto.
