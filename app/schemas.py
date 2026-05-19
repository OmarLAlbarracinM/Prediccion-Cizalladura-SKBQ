from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    metar_observations: Optional[List[str]] = Field(
        default=None,
        description=(
            "Strings METAR crudos en orden cronológico. "
            "Si se omite, la API descarga automáticamente las últimas horas desde SIMFAC."
        ),
    )
    horizon_hours: int = Field(default=6, ge=1, le=12, description="Horas a predecir (1–12)")


class HourForecast(BaseModel):
    step: str = Field(description="Paso de predicción, ej. H+01")
    wind_direction_deg: float = Field(description="Dirección del viento en grados [0, 360)")
    wind_speed_kt: float = Field(description="Velocidad del viento en nudos")
    windshear: Optional[bool] = Field(description="True si hay cizalladura vs hora anterior")
    windshear_cause: str = Field(description="Descripción de la causa de cizalladura")


class PredictResponse(BaseModel):
    airport: str
    prediction_horizon_hours: int
    # Resumen de la primera hora (formato plano para consumo simple)
    wind_direction_deg: float
    wind_speed_kt: float
    wind_gust_kt: float
    windshear_alert: bool
    # Detalle hora a hora
    forecast: List[HourForecast]
    generated_at: str
    model_version: str
    data_source: str = Field(description="'simfac_api' o 'provided'")


class HealthResponse(BaseModel):
    status: str
    model: str
    airport: str
    model_version: str
