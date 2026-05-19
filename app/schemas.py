from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    metar_observations: Optional[List[str]] = Field(
        default=None,
        description="Strings METAR crudos en orden cronologico. Si se omite, la API descarga automaticamente las ultimas horas desde SIMFAC.",
        examples=[
            [
                "SKBO 190000Z 13005KT 9999 FEW020 14/10 Q1025",
                "SKBO 182300Z 12004KT 9999 FEW020 15/11 Q1025",
                "SKBO 182200Z 11003KT 9999 SCT025 15/11 Q1025",
            ]
        ],
    )
    horizon_hours: int = Field(
        default=6,
        ge=1,
        le=12,
        description="Horas a predecir hacia adelante (1 a 12)",
        examples=[6],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "summary": "Descarga automatica desde SIMFAC (recomendado)",
                    "value": {
                        "horizon_hours": 6,
                    },
                },
                {
                    "summary": "Con observaciones METAR propias (requiere minimo 20 registros)",
                    "value": {
                        "metar_observations": [
                            "SKBO 190000Z 13005KT 9999 FEW020 14/10 Q1025",
                            "SKBO 182300Z 12004KT 9999 FEW020 15/11 Q1025",
                            "... (minimo 20 registros horarios)",
                        ],
                        "horizon_hours": 6,
                    },
                },
            ]
        }
    }


class HourForecast(BaseModel):
    step: str = Field(description="Paso de prediccion, ej. H+01", examples=["H+01"])
    wind_direction_deg: float = Field(description="Direccion del viento en grados [0, 360)", examples=[135.0])
    wind_speed_kt: float = Field(description="Velocidad del viento en nudos", examples=[4.2])
    windshear: Optional[bool] = Field(description="True si hay cizalladura respecto a la hora anterior", examples=[False])
    windshear_cause: str = Field(description="Descripcion de la causa de cizalladura", examples=["ninguna"])


class PredictResponse(BaseModel):
    airport: str = Field(examples=["SKBO"])
    prediction_horizon_hours: int = Field(examples=[6])
    wind_direction_deg: float = Field(description="Direccion predicha para H+01 en grados", examples=[135.0])
    wind_speed_kt: float = Field(description="Velocidad predicha para H+01 en nudos", examples=[4.2])
    wind_gust_kt: float = Field(description="Rafaga maxima en el horizonte predicho en nudos", examples=[5.1])
    windshear_alert: bool = Field(description="True si alguna hora del horizonte presenta cizalladura", examples=[True])
    forecast: List[HourForecast]
    generated_at: str = Field(description="Timestamp UTC de generacion en ISO-8601", examples=["2026-05-19T02:00:00Z"])
    model_version: str = Field(examples=["lstm_v1_skbo_20h"])
    data_source: str = Field(description="Fuente de datos: simfac_api o provided", examples=["simfac_api"])


class HealthResponse(BaseModel):
    status: str = Field(examples=["ok"])
    model: str = Field(examples=["loaded"])
    airport: str = Field(examples=["SKBO"])
    model_version: str = Field(examples=["lstm_v1_skbo_20h"])
