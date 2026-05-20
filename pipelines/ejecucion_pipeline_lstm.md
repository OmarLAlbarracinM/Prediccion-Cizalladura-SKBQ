# Instructivo de Ejecución del Pipeline LSTM (API → Predicción)

Este documento describe paso a paso cómo ejecutar el pipeline completo de predicción de viento con el modelo LSTM entrenado en `Prueba_LSTM_pred_cizalladura.ipynb`.

## Flujo del Pipeline

```
┌─────────────────────┐     ┌──────────────────────────┐     ┌─────────────────────┐
│  ventana_metar.py   │────▶│  preparar_datos_lstm.py  │────▶│   prediccion_lstm.py │
│  (descarga API)     │     │  (feature engineering    │     │   (inferencia)       │
│                     │     │   + escalado)            │     │                      │
└─────────────────────┘     └──────────────────────────┘     └─────────────────────┘
```

## Requisitos Previos

1. Tener el entorno virtual activado
2. El modelo entrenado debe estar en `models/best_model_20h.h5`
3. Los scalers del entrenamiento deben estar en `models/scaler_X.pkl` y `models/scaler_y.pkl`

## Regla Importante: Scalers

El modelo fue entrenado con **scalers calculados sobre datos históricos completos (2013-2024)**. Para que las predicciones sean coherentes, al procesar datos nuevos debes usar esos mismos scalers. El pipeline busca automáticamente en `models/`; solo usa `--scalers` si necesitas apuntar a otra ubicación.

| Modo | Comando |
|------|---------|
| **Predicción** (datos nuevos) | Usa `--scalers models/scaler` (o déjalo en blanco, busca en `models/` por defecto) |
| **Entrenamiento** (dataset histórico completo) | Omite `--scalers` (calcula nuevos y los guarda en `models/`) |

---

## Opción 1: PowerShell (recomendada)

```powershell
# 1. Ir al proyecto
cd C:\Users\edwin\OneDrive\Documents\GitHub\Prediccion-Cizalladura-SKBQ

# 2. Activar entorno virtual
.venv\Scripts\Activate.ps1

# 3. Descargar ventana de METAR desde la API (últimas 50 horas)
python pipelines\ventana_metar.py `
    --oaci SKBO `
    --hours 50 `
    --output data\Processed\skbo_ventana.csv

# 4. Preparar datos usando los scalers del entrenamiento
python pipelines\preparar_datos_lstm.py `
    --input data\Processed\skbo_ventana.csv `
    --output data\Processed\skbo_ventana_transformada.csv `
    --scalers models\scaler

# 5. Generar predicción a 6 horas con tabla de Cizalladura y Causa
python pipelines\prediccion_lstm.py `
    --model models\best_model_20h.h5 `
    --input data\Processed\skbo_ventana_transformada.csv `
    --output data\Processed\prediccion_lstm.csv `
    --horizon 6
```

> **Nota:** Si te aparece error de ejecución de scripts en PowerShell, ejecuta primero:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

---

## Opción 2: CMD (Símbolo del sistema)

```cmd
:: 1. Ir al proyecto
cd C:\Users\edwin\OneDrive\Documents\GitHub\Prediccion-Cizalladura-SKBQ

:: 2. Activar entorno virtual
.venv\Scripts\activate.bat

:: 3. Descargar ventana de METAR
python pipelines\ventana_metar.py --oaci SKBO --hours 50 --output data\Processed\skbo_ventana.csv

:: 4. Preparar datos con scalers del entrenamiento
python pipelines\preparar_datos_lstm.py --input data\Processed\skbo_ventana.csv --output data\Processed\skbo_ventana_transformada.csv --scalers models\scaler

:: 5. Generar predicción
python pipelines\prediccion_lstm.py --model models\best_model_20h.h5 --input data\Processed\skbo_ventana_transformada.csv --output data\Processed\prediccion_lstm.csv --horizon 6
```

---

## Opción 3: Git Bash

```bash
# 1. Ir al proyecto
cd /c/Users/edwin/OneDrive/Documents/GitHub/Prediccion-Cizalladura-SKBQ

# 2. Activar entorno virtual
source .venv/Scripts/activate

# 3. Descargar ventana de METAR
python pipelines/ventana_metar.py \
    --oaci SKBO \
    --hours 50 \
    --output data/Processed/skbo_ventana.csv

# 4. Preparar datos con scalers del entrenamiento
python pipelines/preparar_datos_lstm.py \
    --input data/Processed/skbo_ventana.csv \
    --output data/Processed/skbo_ventana_transformada.csv \
    --scalers models/scaler

# 5. Generar predicción
python pipelines/prediccion_lstm.py \
    --model models/best_model_20h.h5 \
    --input data/Processed/skbo_ventana_transformada.csv \
    --output data/Processed/prediccion_lstm.csv \
    --horizon 6
```

---

## Ejemplo de Salida Esperada

```text
============================================================
RESULTADO DE LA PREDICCIÓN LSTM
============================================================
Hora        Dirección   Intensidad    Cizalladura                Causa
----------------------------------------------------------------------
H+01             32.2          3.3           None                   --
H+02             50.4          4.1          False              ninguna
H+03             53.2          4.2          False              ninguna
H+04             47.4          4.1          False              ninguna
H+05             46.2          4.3          False              ninguna
H+06             30.5          3.8          False              ninguna
============================================================
```

**Columnas:**
- **Hora:** H+01 a H+06 (horizonte de predicción)
- **Dirección:** Dirección del viento en grados (0-360°)
- **Intensidad:** Velocidad del viento en nudos (kt)
- **Cizalladura:** `None` (primera hora, no hay referencia), `False` (sin cizalladura) o `True` (con cizalladura)
- **Causa:** Descripción del cambio si hay cizalladura (`ninguna`, `dir ΔXX.X°`, `vel ΔXX.Xkt`, o ambas)

---

## Parámetros Comunes

### `ventana_metar.py`

| Parámetro | Descripción | Default |
|-----------|-------------|---------|
| `--oaci` | Código OACI del aeropuerto | `SKBO` |
| `--hours` | Horas hacia atrás desde la fecha fin | `50` |
| `--end` | Fecha fin `YYYY-MM-DD HH:MM` | Ahora UTC |
| `--output` | Ruta del CSV de salida | `data/Processed/{oaci}_ventana.csv` |

### `preparar_datos_lstm.py`

| Parámetro | Descripción | Default |
|-----------|-------------|---------|
| `--input` | CSV crudo con columna `METAR` | `data/Processed/skbo_ventana.csv` |
| `--output` | CSV transformado | `data/Processed/skbo_ventana_transformada.csv` |
| `--scalers` | Ruta base de scalers pre-entrenados | `None` (modo fit) |

### `prediccion_lstm.py`

| Parámetro | Descripción | Default |
|-----------|-------------|---------|
| `--model` | Ruta del modelo `.h5` | `models/best_model_20h.h5` |
| `--input` | CSV transformado | `data/Processed/skbo_ventana_transformada.csv` |
| `--output` | CSV de predicciones | `data/Processed/prediccion_lstm.csv` |
| `--horizon` | Horas a predecir | `6` |
| `--raw-output` | Solo valores escalados (sin desescalar) | `False` |

---

## Flujo Rápido (si ya descargaste datos)

Si ya tienes `data\Processed\skbo_ventana.csv`, solo ejecuta los pasos 4 y 5:

```powershell
# PowerShell
python pipelines\preparar_datos_lstm.py --input data\Processed\skbo_ventana.csv --output data\Processed\skbo_ventana_transformada.csv --scalers models\scaler

python pipelines\prediccion_lstm.py --model models\best_model_20h.h5 --input data\Processed\skbo_ventana_transformada.csv --output data\Processed\prediccion_lstm.csv --horizon 6
```

---

## Archivos Generados

Después de ejecutar el pipeline completo tendrás:

```
data/Processed/
├── skbo_ventana.csv                  ← datos crudos descargados de la API
├── skbo_ventana_transformada.csv     ← datos normalizados listos para el modelo
└── prediccion_lstm.csv               ← resultado final con predicciones y cizalladura

models/
├── best_model_20h.h5                 ← modelo entrenado
├── scaler_X.pkl                      ← scaler de features
├── scaler_y.pkl                      ← scaler de targets
└── ...
```
