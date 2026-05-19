"""Model loading and autoregressive inference."""
from __future__ import annotations

import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import tensorflow as tf

N_BACK = 20
FEATURES_IN = ["dir_sin", "dir_cos", "intensidad_kt", "temperatura", "rocio"]
TARGETS_OUT = ["dir_sin", "dir_cos", "intensidad_kt"]
MODEL_VERSION = "lstm_v1_skbo_20h"

_MODEL_PATH = Path(os.getenv("MODEL_PATH", "docs/notebooks/best_model_20h.h5"))
_SCALER_X_PATH = Path("models/scaler_X.pkl")
_SCALER_Y_PATH = Path("models/scaler_y.pkl")


def _circular_loss(y_true, y_pred):
    error_sin = tf.square(y_true[:, 0] - y_pred[:, 0])
    error_cos = tf.square(y_true[:, 1] - y_pred[:, 1])
    error_int = tf.square(y_true[:, 2] - y_pred[:, 2])
    return tf.reduce_mean(3.0 * (error_sin + error_cos) + error_int)


def _patch_keras_dense() -> None:
    """Strip quantization_config from Dense.from_config.
    Saved by newer Keras builds but not recognized by the legacy H5 loader in Keras 3.x."""
    from keras.src.layers.core.dense import Dense
    _orig = Dense.from_config.__func__

    @classmethod  # type: ignore[misc]
    def _patched(cls, config):
        config.pop("quantization_config", None)
        return _orig(cls, config)

    Dense.from_config = _patched


class ModelManager:
    def __init__(self) -> None:
        self.model: tf.keras.Model | None = None
        self.scaler_X = None
        self.scaler_y = None
        self.airport_code: str = os.getenv("AIRPORT_CODE", "SKBO")

    @property
    def is_loaded(self) -> bool:
        return self.model is not None

    def load(self) -> None:
        _patch_keras_dense()
        print(f"Cargando modelo: {_MODEL_PATH}")
        self.model = tf.keras.models.load_model(
            _MODEL_PATH,
            custom_objects={"circular_loss": _circular_loss},
        )
        self.scaler_X = joblib.load(_SCALER_X_PATH)
        self.scaler_y = joblib.load(_SCALER_Y_PATH)
        print("Modelo y scalers cargados correctamente.")

    def predict(self, df: pd.DataFrame, horizon: int = 6) -> dict:
        """
        df debe tener al menos N_BACK filas con FEATURES_IN ya escaladas.
        Retorna un dict con predicciones físicas y análisis de cizalladura.
        """
        if self.model is None:
            raise RuntimeError("El modelo no está cargado.")

        ventana = df[FEATURES_IN].iloc[-N_BACK:].to_numpy(dtype=np.float32)
        exog_future = self._get_exog(df, horizon)

        preds_scaled = self._predict_autoregressive(ventana, exog_future, horizon)
        preds_physical = self.scaler_y.inverse_transform(preds_scaled)

        direccion, intensidad = self._to_physical(preds_physical)
        forecast = self._build_forecast(direccion, intensidad)

        return {
            "direccion": direccion,
            "intensidad": intensidad,
            "forecast": forecast,
            "preds_scaled": preds_scaled,
        }

    def _get_exog(self, df: pd.DataFrame, horizon: int) -> np.ndarray:
        exo_cols = ["temperatura", "rocio"]
        disponibles = len(df) - N_BACK
        if disponibles >= horizon:
            return df[exo_cols].iloc[N_BACK : N_BACK + horizon].to_numpy(dtype=np.float32)
        ultimo = df[exo_cols].iloc[-1].to_numpy(dtype=np.float32)
        return np.tile(ultimo, (horizon, 1))

    def _predict_autoregressive(
        self,
        ventana_inicial: np.ndarray,
        exog_future: np.ndarray,
        horizon: int,
    ) -> np.ndarray:
        current = np.expand_dims(ventana_inicial, axis=0)  # (1, N_BACK, 5)
        predicciones = []
        for i in range(horizon):
            next_pred = self.model.predict(current, verbose=0)  # (1, 3)
            predicciones.append(next_pred[0])
            full_step = np.concatenate([next_pred[0], exog_future[i]]).reshape(1, 1, 5)
            current = np.concatenate([current[:, 1:, :], full_step], axis=1)
        return np.array(predicciones, dtype=np.float32)

    @staticmethod
    def _to_physical(preds: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        direccion = np.degrees(np.arctan2(preds[:, 0], preds[:, 1])) % 360
        # scaler_y is identity (mean=0, std=1): model outputs raw kt, clip negative to 0
        intensidad = np.clip(preds[:, 2], 0, None)
        return direccion, intensidad

    @staticmethod
    def _build_forecast(
        direccion: np.ndarray,
        intensidad: np.ndarray,
        umbral_dir: float = 30.0,
        umbral_vel: float = 10.0,
    ) -> list[dict]:
        filas = []
        for h in range(len(direccion)):
            if h == 0:
                cizalladura = None
                causa = "--"
            else:
                delta_dir = abs(direccion[h] - direccion[h - 1])
                delta_dir = min(delta_dir, 360 - delta_dir)
                delta_vel = abs(intensidad[h] - intensidad[h - 1])
                causas = []
                if delta_dir >= umbral_dir:
                    causas.append(f"dir Δ{delta_dir:.1f}°")
                if delta_vel >= umbral_vel:
                    causas.append(f"vel Δ{delta_vel:.1f}kt")
                cizalladura = len(causas) > 0
                causa = ", ".join(causas) if causas else "ninguna"

            filas.append({
                "step": f"H+{h + 1:02d}",
                "wind_direction_deg": round(float(direccion[h]), 1),
                "wind_speed_kt": round(float(intensidad[h]), 2),
                "windshear": cizalladura,
                "windshear_cause": causa,
            })
        return filas
