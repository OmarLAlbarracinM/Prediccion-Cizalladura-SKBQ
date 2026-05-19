from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException

from app.model import ModelManager
from app.preprocessing import build_feature_matrix
from app.schemas import HealthResponse, HourForecast, PredictRequest, PredictResponse

_model = ModelManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _model.load()
    yield


app = FastAPI(
    title="SKBO Wind Prediction API",
    description="Predicción de viento a 6h para el Aeropuerto El Dorado (SKBO) usando LSTM.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        status="ok",
        model="loaded" if _model.is_loaded else "error",
        airport=_model.airport_code,
        model_version="lstm_v1_skbo_20h",
    )


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest = None):
    if request is None:
        request = PredictRequest()

    try:
        df, source = build_feature_matrix(
            metar_strings=request.metar_observations,
            scaler_X=_model.scaler_X,
            airport_code=_model.airport_code,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error en preprocesamiento: {exc}")

    try:
        result = _model.predict(df, horizon=request.horizon_hours)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error en inferencia: {exc}")

    forecast_items = [HourForecast(**f) for f in result["forecast"]]

    # Rafaga: max intensidad predicha (proxy si el modelo no predice rafaga directamente)
    max_gust = max(f.wind_speed_kt for f in forecast_items)
    windshear_alert = any(f.windshear for f in forecast_items if f.windshear is not None)

    first = forecast_items[0]

    return PredictResponse(
        airport=_model.airport_code,
        prediction_horizon_hours=request.horizon_hours,
        wind_direction_deg=first.wind_direction_deg,
        wind_speed_kt=first.wind_speed_kt,
        wind_gust_kt=round(max_gust, 2),
        windshear_alert=windshear_alert,
        forecast=forecast_items,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        model_version="lstm_v1_skbo_20h",
        data_source=source,
    )
