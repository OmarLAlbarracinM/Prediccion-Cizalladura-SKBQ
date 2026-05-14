#!/usr/bin/env python3
"""
Pipeline de predicción LSTM para viento (SKBQ).

Carga el modelo entrenado (models/lstm_model.keras) y los datos de ventana
transformados (data/Processed/skbo_ventana_transformada.csv) para generar
pronósticos autoregresivos a 6 horas de intensidad y dirección del viento.

Requiere los scalers generados por preparar_datos_lstm.py:
- scaler_X.pkl  (en la misma carpeta del CSV de entrada)
- scaler_y.pkl  (en la misma carpeta del CSV de entrada)

Salida:
- CSV con predicciones en data/Processed/prediccion_lstm.csv
- Tabla formateada en consola

Uso:
    python pipelines/prediccion_lstm.py
    python pipelines/prediccion_lstm.py --input data/Processed/skbo_ventana_transformada.csv --output data/Processed/prediccion_lstm.csv --horizon 6
    python pipelines/prediccion_lstm.py --raw-output  # solo valores escalados
"""

from __future__ import annotations

import argparse
import pickle
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.preprocessing import StandardScaler


# =============================================================================
# CONFIGURACIÓN
# =============================================================================
N_BACK = 48  # Ventana histórica que espera el modelo
FEATURES_IN = ["dir_sin", "dir_cos", "intensidad_log", "temperatura", "rocio"]
TARGETS_OUT = ["dir_sin", "dir_cos", "intensidad_log"]
DEFAULT_MODEL = "models/lstm_model.keras"
DEFAULT_INPUT = "data/Processed/skbo_ventana_transformada.csv"
DEFAULT_OUTPUT = "data/Processed/prediccion_lstm.csv"


def circular_loss(y_true, y_pred):
    """Custom loss usada durante el entrenamiento del modelo."""
    error_sin = tf.square(y_true[:, 0] - y_pred[:, 0])
    error_cos = tf.square(y_true[:, 1] - y_pred[:, 1])
    error_dir = error_sin + error_cos
    error_int = tf.square(y_true[:, 2] - y_pred[:, 2])
    return tf.reduce_mean(2.0 * error_dir + error_int)


def cargar_modelo(ruta: Path) -> tf.keras.Model:
    """Carga el modelo .keras registrando la custom loss."""
    print(f"Cargando modelo: {ruta}")
    modelo = tf.keras.models.load_model(
        ruta, custom_objects={"circular_loss": circular_loss}
    )
    print(f"  Input shape:  {modelo.input_shape}")
    print(f"  Output shape: {modelo.output_shape}")
    return modelo


def cargar_datos(ruta: Path) -> pd.DataFrame:
    """Carga el CSV transformado y valida columnas mínimas."""
    print(f"Cargando datos: {ruta}")
    df = pd.read_csv(ruta, parse_dates=["FECHA_REPORTE"])

    faltantes = [c for c in FEATURES_IN if c not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas requeridas en el CSV: {faltantes}")

    # Asegurar orden cronológico
    df = df.sort_values("FECHA_REPORTE").reset_index(drop=True)
    print(f"  Registros: {len(df)}")
    print(f"  Rango: {df['FECHA_REPORTE'].min()} -> {df['FECHA_REPORTE'].max()}")
    return df


def cargar_scalers(ruta_csv: Path) -> tuple[StandardScaler | None, StandardScaler | None]:
    """Carga scaler_X y scaler_y desde la misma carpeta del CSV de entrada."""
    carpeta = ruta_csv.parent
    ruta_scaler_x = carpeta / "scaler_X.pkl"
    ruta_scaler_y = carpeta / "scaler_y.pkl"

    if not ruta_scaler_x.exists() or not ruta_scaler_y.exists():
        print(
            "  ADVERTENCIA: No se encontraron scalers. "
            "Ejecuta: python pipelines/preparar_datos_lstm.py"
        )
        return None, None

    with open(ruta_scaler_x, "rb") as f:
        scaler_X = pickle.load(f)
    with open(ruta_scaler_y, "rb") as f:
        scaler_y = pickle.load(f)

    print(f"  scaler_X cargado: {ruta_scaler_x}")
    print(f"  scaler_y cargado: {ruta_scaler_y}")
    return scaler_X, scaler_y


def preparar_ventana_inicial(df: pd.DataFrame) -> np.ndarray:
    """Extrae los últimos N_BACK registros con las 5 features de entrada."""
    if len(df) < N_BACK:
        raise ValueError(
            f"Se requieren al menos {N_BACK} registros de historia. "
            f"El CSV tiene {len(df)}."
        )

    ventana = df[FEATURES_IN].iloc[-N_BACK:].to_numpy(dtype=np.float32)
    return ventana  # forma (N_BACK, 5)


def obtener_exogenas_futuras(df: pd.DataFrame, horizon: int) -> np.ndarray:
    """
    Obtiene temperatura y rocío para las H horas futuras.
    Si no hay suficientes datos, repite el último valor conocido (forward-fill).
    """
    exo_cols = ["temperatura", "rocio"]

    # Registros disponibles después de la ventana histórica
    disponibles = len(df) - N_BACK

    if disponibles >= horizon:
        # Tenemos datos exógenos reales para todo el horizonte
        exo = df[exo_cols].iloc[N_BACK : N_BACK + horizon].to_numpy(dtype=np.float32)
    else:
        # Forward-fill con el último valor conocido
        ultimo = df[exo_cols].iloc[-1].to_numpy(dtype=np.float32)
        exo = np.tile(ultimo, (horizon, 1))
        if horizon - disponibles > 0:
            warnings.warn(
                f"Solo hay {disponibles} registros futuros disponibles. "
                f"Se rellenan las {horizon - disponibles} horas restantes con "
                f"forward-fill (último valor conocido).",
                UserWarning,
            )

    return exo  # forma (horizon, 2)


def predecir_autoregresivo(
    modelo: tf.keras.Model,
    ventana_inicial: np.ndarray,
    exog_future: np.ndarray,
    horizon: int,
) -> np.ndarray:
    """
    Predicción iterativa (autoregresiva) a `horizon` pasos.

    Returns
    -------
    np.ndarray
        Predicciones de forma (horizon, 3) -> [dir_sin, dir_cos, intensidad_log] (escaladas).
    """
    current_window = np.copy(ventana_inicial)
    current_window = np.expand_dims(current_window, axis=0)  # (1, N_BACK, 5)

    predicciones = []

    for i in range(horizon):
        # 1. Predicción del modelo (1, 3)
        next_step_pred = modelo.predict(current_window, verbose=0)

        # 2. Guardar predicción
        predicciones.append(next_step_pred[0])

        # 3. Construir el siguiente timestep completo (5 variables)
        temp_rocio = exog_future[i]  # (2,)
        full_step = np.concatenate([next_step_pred[0], temp_rocio])  # (5,)
        full_step_3d = full_step.reshape(1, 1, 5)

        # 4. Deslizar ventana
        current_window = np.concatenate(
            [current_window[:, 1:, :], full_step_3d], axis=1
        )

    return np.array(predicciones, dtype=np.float32)  # (horizon, 3)


def convertir_a_fisico(preds_descaled: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Convierte predicciones desescaladas a magnitudes operacionales.

    Returns
    -------
    direccion : np.ndarray
        Dirección del viento en grados [0, 360).
    intensidad : np.ndarray
        Intensidad del viento en nudos (kt).
    """
    sin_pred = preds_descaled[:, 0]
    cos_pred = preds_descaled[:, 1]
    intensidad_log = preds_descaled[:, 2]

    # Dirección meteorológica (de dónde viene el viento)
    direccion = np.degrees(np.arctan2(sin_pred, cos_pred)) % 360

    # Intensidad: inverso de log1p
    intensidad = np.expm1(intensidad_log)

    return direccion, intensidad


def guardar_resultados(
    ruta: Path,
    fechas: pd.DatetimeIndex,
    direccion: np.ndarray | None,
    intensidad: np.ndarray | None,
    preds_scaled: np.ndarray,
) -> None:
    """Exporta el forecast a CSV."""
    ruta.parent.mkdir(parents=True, exist_ok=True)

    data: dict = {
        "FECHA_HORA": fechas,
        "DIR_SIN_SCALED": np.round(preds_scaled[:, 0], 6),
        "DIR_COS_SCALED": np.round(preds_scaled[:, 1], 6),
        "INTENSIDAD_LOG_SCALED": np.round(preds_scaled[:, 2], 6),
    }

    if direccion is not None and intensidad is not None:
        data["DIRECCION_GRADOS"] = np.round(direccion, 1)
        data["INTENSIDAD_KT"] = np.round(intensidad, 2)

    df_out = pd.DataFrame(data)
    df_out.to_csv(ruta, index=False)
    print(f"\nPredicción guardada: {ruta}")


def imprimir_tabla(
    fechas: pd.DatetimeIndex,
    direccion: np.ndarray | None,
    intensidad: np.ndarray | None,
    preds_scaled: np.ndarray,
) -> None:
    """Muestra resultados formateados en consola."""
    print("\n" + "=" * 60)
    print("RESULTADO DE LA PREDICCIÓN LSTM")
    print("=" * 60)

    if direccion is not None and intensidad is not None:
        print(f"{'Hora':<20} {'Dirección (°)':>15} {'Intensidad (kt)':>18}")
        print("-" * 60)
        for i in range(len(fechas)):
            dir_str = f"{direccion[i]:.1f}"
            int_str = f"{intensidad[i]:.2f}"
            # Post-proceso RAC 12: VRB si intensidad < 3 kt
            if intensidad[i] < 3.0:
                dir_str = "VRB"
            print(f"{str(fechas[i]):<20} {dir_str:>15} {int_str:>18}")
    else:
        print("Valores escalados (output crudo del modelo):")
        print(f"{'Hora':<20} {'dir_sin':>12} {'dir_cos':>12} {'intensidad_log':>16}")
        print("-" * 60)
        for i in range(len(fechas)):
            print(
                f"{str(fechas[i]):<20} "
                f"{preds_scaled[i, 0]:>12.4f} "
                f"{preds_scaled[i, 1]:>12.4f} "
                f"{preds_scaled[i, 2]:>16.4f}"
            )

    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Predicción LSTM de viento a 6 horas usando modelo entrenado"
    )
    parser.add_argument(
        "--model", default=DEFAULT_MODEL, help="Ruta del modelo .keras"
    )
    parser.add_argument(
        "--input", default=DEFAULT_INPUT, help="Ruta del CSV transformado"
    )
    parser.add_argument(
        "--output", default=DEFAULT_OUTPUT, help="Ruta de salida del CSV"
    )
    parser.add_argument(
        "--horizon",
        type=int,
        default=6,
        help="Horizonte de predicción en horas (default: 6)",
    )
    parser.add_argument(
        "--raw-output",
        action="store_true",
        help="Devuelve solo los valores escalados sin intentar convertir a físico",
    )
    args = parser.parse_args()

    ruta_input = Path(args.input).resolve()

    # ------------------------------------------------------------------
    # 1. Cargar recursos
    # ------------------------------------------------------------------
    modelo = cargar_modelo(Path(args.model))
    df = cargar_datos(ruta_input)
    scaler_X, scaler_y = cargar_scalers(ruta_input)

    # ------------------------------------------------------------------
    # 2. Preparar ventanas
    # ------------------------------------------------------------------
    ventana_inicial = preparar_ventana_inicial(df)
    exog_future = obtener_exogenas_futuras(df, args.horizon)

    print(f"\nVentana inicial : {ventana_inicial.shape}")
    print(f"Exógenas futuras: {exog_future.shape}")

    # ------------------------------------------------------------------
    # 3. Predicción autoregresiva
    # ------------------------------------------------------------------
    print(f"\nGenerando predicción a {args.horizon} horas...")
    preds_scaled = predecir_autoregresivo(
        modelo, ventana_inicial, exog_future, args.horizon
    )

    # ------------------------------------------------------------------
    # 4. Post-proceso (desescalado + conversión física)
    # ------------------------------------------------------------------
    direccion: np.ndarray | None = None
    intensidad: np.ndarray | None = None

    if not args.raw_output and scaler_y is not None:
        preds_descaled = scaler_y.inverse_transform(preds_scaled)
        direccion, intensidad = convertir_a_fisico(preds_descaled)

        # Validación de coherencia
        tiene_negativos = np.any(intensidad < 0)
        tiene_nan = np.any(np.isnan(intensidad))
        tiene_inf = np.any(np.isinf(intensidad))
        max_intensidad = np.max(intensidad)

        if tiene_negativos or tiene_nan or tiene_inf or max_intensidad < 1.0:
            print("\n" + "!" * 60)
            print("ADVERTENCIA: Las predicciones desescaladas no son coherentes.")
            print(f"  - Intensidad máxima: {max_intensidad:.2f} kt")
            print(f"  - Valores negativos: {tiene_negativos}")
            print(f"  - NaN: {tiene_nan} | Inf: {tiene_inf}")
            print("\nEsto suele ocurrir cuando el modelo fue entrenado con scalers")
            print("diferentes a los del conjunto de entrada actual.")
            print("\nSugerencias:")
            print("  1. Reentrena el modelo usando datos procesados por")
            print("     'preparar_datos_lstm.py' (ahora guarda scalers).")
            print("  2. Usa --raw-output para obtener los valores escalados.")
            print("!" * 60)
            # Fallback a raw
            direccion = None
            intensidad = None
    elif args.raw_output:
        print("\nModo --raw-output: se omiten desescalado y conversión física.")
    else:
        print(
            "\nNo se encontraron scalers. Ejecuta 'preparar_datos_lstm.py' primero "
            "o usa --raw-output."
        )

    # Fechas futuras
    ultima_fecha = df["FECHA_REPORTE"].iloc[-1]
    fechas_futuras = pd.date_range(
        start=ultima_fecha + pd.Timedelta(hours=1),
        periods=args.horizon,
        freq="h",
    )

    # ------------------------------------------------------------------
    # 5. Exportar y mostrar
    # ------------------------------------------------------------------
    guardar_resultados(
        Path(args.output), fechas_futuras, direccion, intensidad, preds_scaled
    )
    imprimir_tabla(fechas_futuras, direccion, intensidad, preds_scaled)


if __name__ == "__main__":
    main()
