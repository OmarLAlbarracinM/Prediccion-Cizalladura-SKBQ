# pipelines/ — Scripts Reutilizables de Datos y Predicción

## Descripción

Colección de scripts Python que implementan el flujo completo de datos
del proyecto: desde la **descarga** de reportes meteorológicos METAR,
pasando por el **preprocesamiento**, la **ingeniería de features**,
hasta la **predicción** con el modelo LSTM entrenado.

Cada script está diseñado como un módulo reutilizable que puede
ejecutarse desde la línea de comandos con `argparse`, o importarse como
biblioteca desde otros scripts o notebooks.

## Estructura

```
pipelines/
├── README.md                          # Este archivo
├── ejecucion_pipeline_lstm.md         # Guía paso a paso para ejecutar el pipeline completo
│
│  ── Descarga de datos ──
├── consultar_api_metar.py             # Módulo de bajo nivel para consultar la API SIMFAC
├── ventana_metar.py                   # Descarga una ventana temporal de METAR
│
│  ── Ingesta y preprocesamiento ──
├── ingestion_new_data.py              # Unión de nuevos datos + versionado DVC
├── preprocesamiento_metar.py          # Limpieza y extracción de variables METAR
│
│  ── Preparación y predicción ──
├── preparar_datos_lstm.py             # Feature engineering + escalado para LSTM
└── prediccion_lstm.py                 # Inferencia autoregresiva con modelo LSTM
```

## Flujo completo de datos

```
     ┌──────────────────────┐
     │   API SIMFAC (web)   │
     └──────────┬───────────┘
                │
    ┌───────────▼────────────┐        ┌────────────────────────┐
    │  consultar_api_metar   │        │   ingestion_new_data   │
    │  (descarga por rango)  │        │   (une nuevos datos    │
    └───────────┬────────────┘        │    + backup + DVC)     │
                │                     └───────────┬────────────┘
    ┌───────────▼────────────┐                    │
    │    ventana_metar       │        ┌───────────▼────────────┐
    │  (ventana de N horas)  │        │ preprocesamiento_metar │
    └───────────┬────────────┘        │ (limpieza + variables) │
                │                     └───────────┬────────────┘
                ▼                                 ▼
    data/Processed/skbo_ventana.csv   data/raw/DATOS_PROCESADOS.csv
                │
    ┌───────────▼────────────┐
    │  preparar_datos_lstm   │
    │  (features + escalado) │
    └───────────┬────────────┘
                │
                ▼
    data/Processed/skbo_ventana_transformada.csv
                │
    ┌───────────▼────────────┐
    │    prediccion_lstm     │
    │   (inferencia LSTM)    │
    └───────────┬────────────┘
                │
                ▼
    data/Processed/prediccion_lstm.csv
```

---

## Scripts en detalle

### 1. `consultar_api_metar.py` — Descarga de METAR desde SIMFAC

**Qué hace:** consulta la API REST pública del SIMFAC (Sistema de
Información de la Fuerza Aérea Colombiana) para obtener reportes METAR
de cualquier aeropuerto colombiano identificado por su código OACI.

**Por qué se hizo:** la fuente primaria de datos meteorológicos del
proyecto es la API de SIMFAC. Este módulo encapsula la lógica de
conexión, parsing del JSON anidado y exportación a CSV, de modo que
otros scripts y la API FastAPI puedan reutilizarlo.

**Funciones principales:**

| Función | Descripción |
|---------|-------------|
| `convertir_a_unix(fecha_str)` | Convierte una fecha ISO (`YYYY-MM-DD` o `YYYY-MM-DD HH:MM`) a timestamp Unix UTC. |
| `obtener_metar(oaci, begin_date, end_date)` | Realiza la petición HTTP GET a la API SIMFAC y retorna el JSON. Maneja errores HTTP, de conexión y de parsing. |
| `metar_a_dataframe(datos_api)` | Aplana la estructura JSON anidada `{oaci: [{Airport, METARES: [{Date, METAR}]}]}` en un DataFrame plano con columnas OACI, Aeropuerto, coordenadas, fecha y texto METAR. |
| `guardar_csv(df, ruta)` | Exporta a CSV creando directorios intermedios si no existen. |
| `consultar_metar(oaci, start, end, days, output)` | Función de alto nivel que combina las anteriores. Acepta fechas explícitas o últimos N días. |

**Uso:**

```bash
# Descargar METAR por rango de fechas
python pipelines/consultar_api_metar.py --oaci SKBO --start 2024-06-01 --end 2024-06-30

# Descargar últimos 14 días
python pipelines/consultar_api_metar.py --oaci SKBO --days 14

# Guardar en ruta personalizada
python pipelines/consultar_api_metar.py --oaci SKBQ --days 7 --output data/raw/skbq_latest.csv
```

**Infraestructura:**

- Usa `urllib.request` (stdlib) en lugar de `requests` para evitar
  dependencias adicionales.
- Timeout de 30 segundos para evitar bloqueos en caso de problemas de red.
- El endpoint de la API es: `https://simfac.fac.mil.co/api/1.0/metaresForOacisForTimes`

---

### 2. `ventana_metar.py` — Descarga de ventana temporal

**Qué hace:** descarga los METAR de las últimas N horas desde una fecha
fin (por defecto, ahora UTC). Es un wrapper de `consultar_api_metar.py`
optimizado para el caso de uso de inferencia: obtener exactamente la
ventana temporal que el modelo necesita.

**Por qué se hizo:** el modelo LSTM requiere una ventana mínima de 20
horas de historia (`N_BACK = 20`). En la práctica se descargan 50 horas
para tener margen de limpieza (registros NIL, gaps, duplicados).

**Funciones principales:**

| Función | Descripción |
|---------|-------------|
| `descargar_ventana(oaci, end, hours, output)` | Calcula el rango de timestamps, llama a `obtener_metar()` y guarda el resultado. |

**Uso:**

```bash
# Últimas 50 horas (default)
python pipelines/ventana_metar.py

# Últimas 24 horas para SKBO
python pipelines/ventana_metar.py --oaci SKBO --hours 24

# Ventana específica con fecha fin
python pipelines/ventana_metar.py --oaci SKBQ --end "2024-06-30 12:00" --hours 50
```

**Infraestructura:**

- Reutiliza las funciones de `consultar_api_metar.py` mediante import
  con fallback (`try/except ImportError`) para funcionar tanto ejecutado
  desde la raíz del proyecto como desde la carpeta `pipelines/`.
- La salida por defecto es `data/Processed/{oaci}_ventana.csv`.

---

### 3. `ingestion_new_data.py` — Ingesta y versionado de nuevos datos

**Qué hace:** une el dataset maestro (`data/raw/DATOS_CRUDOS.csv`) con
un archivo de nuevos datos, crea un backup del original, deduplica,
guarda el resultado y lo versiona con DVC.

**Por qué se hizo:** el dataset maestro crece a medida que se recopilan
nuevos reportes METAR. Este script automatiza el proceso de ingesta
garantizando integridad (backup, validación de columnas, deduplicación)
y trazabilidad (versionado DVC con Git).

**Funciones principales:**

| Función | Descripción |
|---------|-------------|
| `ensure_directories(raw_dir, new_data_dir)` | Crea los directorios necesarios si no existen. |
| `find_bad_lines(csv_path, output_path)` | Escanea el CSV línea por línea buscando filas malformadas (comillas impares). Exporta un reporte de líneas problemáticas. |
| `read_new_data(new_path)` | Lee archivos nuevos con detección automática de formato (CSV con `;` o Excel `.xlsx`). |
| `load_data(raw_path, new_path)` | Carga ambos datasets con manejo de errores de parsing. |
| `validate_columns(df_raw, df_new)` | Verifica que las columnas del archivo nuevo coincidan exactamente con las del maestro. |
| `combine_datasets(df_raw, df_new)` | Concatena, deduplica por `(FECHA_REPORTE, HORA_REPORTE, TIPO_REPORTE)` y ordena cronológicamente. |
| `backup_file(raw_path, backup_dir)` | Crea una copia de seguridad con timestamp en el nombre: `DATOS_CRUDOS_backup_YYYYMMDD_HHMMSS.csv`. |
| `save_dataset(df, raw_path)` | Sobrescribe el dataset maestro con los datos unidos. |
| `dvc_add(path)` | Ejecuta `dvc add` para registrar la nueva versión del archivo. |

**Uso:**

```bash
# Con rutas por defecto
python pipelines/ingestion_new_data.py

# Con rutas explícitas
python pipelines/ingestion_new_data.py \
    --raw data/raw/DATOS_CRUDOS.csv \
    --new data/NewData/skbo.csv \
    --backup-dir data/raw
```

**Infraestructura:**

- Requiere [DVC](https://dvc.org/) instalado (`pip install dvc`).
- Después de ejecutar, el usuario debe hacer:
  ```bash
  git add data/raw/DATOS_CRUDOS.csv.dvc data/raw/.gitignore
  git commit -m "data: ingesta de nuevos datos METAR"
  dvc push
  ```

---

### 4. `preprocesamiento_metar.py` — Limpieza y extracción de variables

**Qué hace:** toma el CSV crudo de METAR (`DATOS_CRUDOS.csv`) y genera
un CSV procesado (`DATOS_PROCESADOS.csv`) con variables meteorológicas
extraídas: aeródromo, hora zulú, viento, visibilidad, nubosidad,
temperatura/rocío, presión y fenómenos significativos.

**Por qué se hizo:** los reportes METAR son cadenas de texto codificadas
según el estándar OACI/WMO. Para usarlos en análisis o modelos de ML,
es necesario parsear cada campo. Este pipeline replica las
transformaciones del notebook `docs/notebooks/02_preprocesamiento.ipynb`.

**Funciones principales:**

| Función | Descripción |
|---------|-------------|
| `cargar_datos(ruta_csv)` | Lee el CSV crudo. |
| `eliminar_registros_invalidos(df)` | Filtra reportes con contenido `"NIL"` (reportes cancelados o no disponibles). |
| `normalizar_fechas(df)` | Convierte la columna de fecha a datetime, elimina registros con año 1900 (fecha inválida). |
| `tokenizar_metar(df)` | Divide la cadena METAR en tokens (palabras) para facilitar la extracción posicional. |
| `extraer_variables_meteorologicas(df)` | Extrae: aeródromo (token 0), hora zulú (token 1), viento (token 2), visibilidad (token 3), temperatura/rocío (regex), presión (regex `A\d{4}`), nubosidad (regex `FEW/SCT/BKN/OVC`), fenómenos (`TS/RA/SHRA/FG/BR/HZ/CB`). |
| `agregar_componentes_viento(df)` | Descompone el campo de viento en dirección (grados) y velocidad (nudos). |
| `crear_dataset_procesado(df)` | Selecciona las columnas finales del dataset procesado. |
| `exportar_dataset(df, ruta)` | Guarda el resultado como CSV. |

**Uso:**

```bash
python pipelines/preprocesamiento_metar.py

python pipelines/preprocesamiento_metar.py \
    --input data/raw/DATOS_CRUDOS.csv \
    --output data/raw/DATOS_PROCESADOS.csv
```

---

### 5. `preparar_datos_lstm.py` — Feature engineering para LSTM

**Qué hace:** transforma un CSV con METAR parseados en un dataset listo
para ser consumido por el modelo LSTM. Aplica: filtrado de outliers,
conversión a componentes circulares, resampleo horario, interpolación
lineal y normalización con `StandardScaler`.

**Por qué se hizo:** el modelo LSTM espera una entrada muy específica:
5 features numéricas (`dir_sin`, `dir_cos`, `intensidad_kt`,
`temperatura`, `rocio`) normalizadas y a frecuencia horaria. Este
pipeline replica exactamente las transformaciones del notebook
`docs/experimentos_notebooks/08_prueba_lstm_pred_cizalladura.ipynb`.

**Funciones principales:**

| Función | Descripción |
|---------|-------------|
| `cargar_datos(ruta)` | Lee el CSV y lo valida. |
| `eliminar_registros_nil(df)` | Filtra reportes NIL. |
| `normalizar_fechas(df)` | Convierte fechas, elimina año 1900. |
| `tokenizar_y_limpiar_metar(df)` | Tokeniza, elimina keyword `AUTO`, filtra por longitud de tokens. |
| `extraer_variables(df)` | Extrae viento, temperatura y rocío usando regex. |
| `seleccionar_columnas_base(df)` | Reduce a las columnas necesarias. |
| `procesar_viento(df)` | Parsea dirección/velocidad/ráfaga, aplica forward-fill a VRB, cap a 40 kt, redondea a hora, genera `dir_sin` y `dir_cos`. |
| `resamplear_e_interpolar(df)` | Resamplea a frecuencia horaria con agregación (mean para dir/intensidad/temp, max para ráfaga). Interpola gaps linealmente. |
| `normalizar_con_scaler(df, ruta_scalers)` | **Modo fit:** calcula nuevos scalers y los guarda en `models/`. **Modo transform:** aplica scalers pre-existentes (para inferencia). |
| `exportar_dataset(df, ruta_csv)` | Guarda el CSV transformado. |

**Dos modos de operación:**

| Modo | Cuándo usarlo | Comando |
|------|--------------|---------|
| **Entrenamiento** (`fit`) | Cuando reentrenamos el modelo con datos nuevos | `python pipelines/preparar_datos_lstm.py --input ... --output ...` |
| **Predicción** (`transform`) | Cuando hacemos inferencia con datos recientes | `python pipelines/preparar_datos_lstm.py --input ... --output ... --scalers models/scaler` |

La diferencia crítica: en modo entrenamiento se calcula la media y
desviación estándar de los datos. En modo predicción se **reutilizan**
las estadísticas calculadas durante el entrenamiento para mantener
coherencia.

**Uso:**

```bash
# Modo entrenamiento (genera scalers en models/)
python pipelines/preparar_datos_lstm.py \
    --input data/Processed/skbo_ventana.csv \
    --output data/Processed/skbo_ventana_transformada.csv

# Modo predicción (usa scalers existentes)
python pipelines/preparar_datos_lstm.py \
    --input data/Processed/skbo_ventana.csv \
    --output data/Processed/skbo_ventana_transformada.csv \
    --scalers models/scaler
```

---

### 6. `prediccion_lstm.py` — Inferencia con el modelo LSTM

**Qué hace:** carga el modelo LSTM entrenado y genera un pronóstico
autoregresivo de dirección, velocidad del viento y alertas de
cizalladura para las próximas N horas.

**Por qué se hizo:** encapsula la lógica de inferencia del notebook
`08_prueba_lstm_pred_cizalladura.ipynb` en un script reproducible y
automatizable.

**Funciones principales:**

| Función | Descripción |
|---------|-------------|
| `circular_loss(y_true, y_pred)` | Custom loss requerida para deserializar el modelo `.h5`. |
| `cargar_modelo(ruta)` | Carga el modelo con `custom_objects`. |
| `cargar_datos(ruta)` | Lee y valida el CSV transformado. |
| `cargar_scalers(ruta_csv)` | Busca scalers en `models/` (prioridad) o en la carpeta del CSV. |
| `preparar_ventana_inicial(df)` | Extrae los últimos 20 registros como ventana inicial. |
| `obtener_exogenas_futuras(df, horizon)` | Extrae temperatura y rocío para las horas futuras (o forward-fill si no hay datos). |
| `predecir_autoregresivo(modelo, ventana, exog, horizon)` | Bucle de predicción iterativa. En cada paso: predice → concatena → desliza ventana. |
| `convertir_a_fisico(preds_descaled)` | Convierte `(dir_sin, dir_cos)` → grados, recorta intensidad negativa. |
| `generar_pronostico_df(direccion, intensidad)` | Crea DataFrame con análisis de cizalladura hora a hora. |
| `guardar_resultados(...)` | Exporta CSV con predicciones escaladas y físicas. |
| `imprimir_tabla(...)` | Muestra tabla formateada en consola. |

**Análisis de cizalladura:**

Se aplican dos umbrales entre horas consecutivas:
- **Dirección:** cambio ≥ 30° (ajustado por circularidad: `min(Δ, 360-Δ)`)
- **Velocidad:** cambio ≥ 10 kt

Si alguno se supera, se genera alerta con la causa específica.

**Uso:**

```bash
# Con defaults
python pipelines/prediccion_lstm.py

# Con parámetros explícitos
python pipelines/prediccion_lstm.py \
    --model models/best_model_20h.h5 \
    --input data/Processed/skbo_ventana_transformada.csv \
    --output data/Processed/prediccion_lstm.csv \
    --horizon 6

# Solo valores escalados (sin desescalar)
python pipelines/prediccion_lstm.py --raw-output
```

---

### `ejecucion_pipeline_lstm.md` — Guía de ejecución

Documento paso a paso que explica cómo ejecutar el pipeline completo
(descarga → preparación → predicción) en Windows (PowerShell, CMD) y
Unix (Bash). Incluye ejemplos de salida, parámetros y troubleshooting.

---

## Infraestructura

### Dependencias

Todos los scripts usan las mismas dependencias definidas en
`requirements.txt`:

```
pandas, numpy, scikit-learn, tensorflow, joblib
```

Adicionalmente, `ingestion_new_data.py` requiere `dvc` instalado.

### Ejecución

Todos los scripts esperan ser ejecutados **desde la raíz del proyecto**:

```bash
python pipelines/<script>.py [--opciones]
```

Esto es importante porque las rutas relativas (`models/`, `data/`) se
resuelven desde el directorio de trabajo actual.

### Variables de entorno

Los pipelines **no** usan variables de entorno. Toda la configuración
se pasa por argumentos CLI. La excepción es la API FastAPI (`app/`),
que sí usa `MODEL_PATH` y `AIRPORT_CODE`.

### Relación con la API

La API FastAPI (`app/`) contiene su propia copia simplificada de la
lógica de preprocesamiento y predicción (`app/preprocessing.py` y
`app/model.py`). Esto es intencional: la API debe ser autocontenida
y no depender de los scripts de `pipelines/`.

```
pipelines/                           app/
  consultar_api_metar.py    ←─→    preprocessing.py (descarga SIMFAC)
  preparar_datos_lstm.py    ←─→    preprocessing.py (feature engineering)
  prediccion_lstm.py        ←─→    model.py (ModelManager)
```

Ambas implementaciones deben mantenerse sincronizadas si se cambian las
transformaciones o la lógica de inferencia.
