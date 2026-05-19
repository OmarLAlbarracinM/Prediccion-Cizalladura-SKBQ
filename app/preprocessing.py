"""METAR preprocessing pipeline for API inference.

Replicates preparar_datos_lstm.py but uses pre-trained scalers (transform, not fit_transform)
and accepts either raw METAR strings or auto-fetches from SIMFAC API.
"""
from __future__ import annotations

import json
import re
import urllib.request
import warnings
from datetime import datetime, timedelta, timezone
from typing import Optional

import numpy as np
import pandas as pd

FEATURES_IN = ["dir_sin", "dir_cos", "intensidad_kt", "temperatura", "rocio"]
N_BACK = 20
SIMFAC_URL = "https://simfac.fac.mil.co/api/1.0/metaresForOacisForTimes"
_DEFAULT_LOOKBACK_HOURS = 30  # >N_BACK to have margin after cleaning


# ---------------------------------------------------------------------------
# SIMFAC API
# ---------------------------------------------------------------------------

def _fetch_simfac(oaci: str, hours: int = _DEFAULT_LOOKBACK_HOURS) -> pd.DataFrame:
    now = datetime.now(timezone.utc)
    begin = int((now - timedelta(hours=hours)).timestamp())
    end = int(now.timestamp())
    url = f"{SIMFAC_URL}?beginDate={begin}&endDate={end}&oacis={oaci}"

    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    records = []
    for _, airports in data.items():
        for airport in airports:
            for entry in airport.get("METARES", []):
                records.append({
                    "FECHA_HORA_REPORTE": entry.get("Date", ""),
                    "METAR": entry.get("METAR", ""),
                })

    df = pd.DataFrame(records)
    if not df.empty:
        df["FECHA_HORA_REPORTE"] = pd.to_datetime(
            df["FECHA_HORA_REPORTE"], format="%d-%m-%Y %H:%M:%S", errors="coerce"
        )
    return df


# ---------------------------------------------------------------------------
# METAR string parsing
# ---------------------------------------------------------------------------

def _parse_metar_strings(metar_list: list[str]) -> pd.DataFrame:
    """Convert raw METAR strings to a DataFrame with FECHA_HORA_REPORTE and METAR columns."""
    now = datetime.now(timezone.utc)
    records = []
    for raw in metar_list:
        raw = raw.strip()
        tokens = raw.split()
        if len(tokens) < 3:
            continue
        # Parse timestamp token like '181400Z' (day=18, hour=14, minute=00)
        ts_token = tokens[1] if len(tokens) > 1 else ""
        match = re.match(r"^(\d{2})(\d{2})(\d{2})Z$", ts_token)
        if match:
            day, hour, minute = int(match.group(1)), int(match.group(2)), int(match.group(3))
            try:
                dt = now.replace(day=day, hour=hour, minute=minute, second=0, microsecond=0)
            except ValueError:
                dt = now
        else:
            dt = now
        records.append({"FECHA_HORA_REPORTE": dt, "METAR": raw})

    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Feature extraction (mirrors preparar_datos_lstm.py)
# ---------------------------------------------------------------------------

_VIENTO_RE = re.compile(r"^(\d{3}|VRB)(\d{2,3})(G\d{2,3})?KT$")


def _parse_viento(cadena: str) -> tuple[Optional[float], Optional[float], float]:
    if not cadena or not isinstance(cadena, str):
        return None, None, 0.0
    cadena = re.sub(r"[A-Za-z]{3}$", "KT", cadena)
    m = _VIENTO_RE.match(cadena)
    if not m:
        return None, None, 0.0
    direccion = float(m.group(1)) if m.group(1) != "VRB" else None
    velocidad = float(m.group(2))
    rafaga = float(m.group(3)[1:]) if m.group(3) else 0.0
    return direccion, velocidad, rafaga


def _buscar_temp_rocio(tokens: list[str]) -> tuple[Optional[float], Optional[float]]:
    patron = re.compile(r"^M?(\d{1,2})/M?(\d{1,2})$")
    for t in tokens:
        m = patron.match(t)
        if m:
            return float(m.group(1)), float(m.group(2))
    return None, None


def _extract_features(df: pd.DataFrame) -> pd.DataFrame:
    """From a DataFrame with FECHA_HORA_REPORTE and METAR, extract wind/temp features."""
    df = df.dropna(subset=["METAR"]).copy()
    df = df[~df["METAR"].str.contains("NIL", na=False)].copy()

    # Tokenize and clean AUTO
    df["tokens"] = (
        df["METAR"]
        .str.replace(r"\bAUTO\b\s?", "", regex=True, flags=re.IGNORECASE)
        .str.strip()
        .str.split()
    )

    # Filter malformed rows
    df = df[df["tokens"].str.len() >= 4].copy()
    df = df[df["tokens"].str[2].str.len().isin([6, 7, 8, 9, 10])].copy()

    df["viento_raw"] = df["tokens"].str[2]
    parsed = df["viento_raw"].apply(lambda v: pd.Series(_parse_viento(v), index=["direccion", "intensidad_kt", "rafaga_kt"]))
    df = pd.concat([df, parsed], axis=1)

    temp_rocio = df["tokens"].apply(lambda t: pd.Series(_buscar_temp_rocio(t), index=["temperatura", "rocio"]))
    df = pd.concat([df, temp_rocio], axis=1)

    df["temperatura"] = pd.to_numeric(df["temperatura"], errors="coerce")
    df["rocio"] = pd.to_numeric(df["rocio"], errors="coerce")

    # Forward-fill direction for VRB reports
    df["direccion"] = df["direccion"].ffill()

    df = df[df["intensidad_kt"].notnull()].copy()
    df = df[df["direccion"].notnull()].copy()
    df = df[df["direccion"] <= 360].copy()

    # Cap outlier wind speeds
    df.loc[df["intensidad_kt"] > 40, "intensidad_kt"] = np.nan

    df["dir_sin"] = np.sin(np.radians(df["direccion"]))
    df["dir_cos"] = np.cos(np.radians(df["direccion"]))

    df["FECHA_HORA_REPORTE"] = pd.to_datetime(df["FECHA_HORA_REPORTE"])
    df = df.set_index("FECHA_HORA_REPORTE").sort_index()
    df.index = df.index.round("h")
    df = df[~df.index.duplicated(keep="last")].copy()

    return df


def _resample_and_fill(df: pd.DataFrame) -> pd.DataFrame:
    cols = {
        "dir_sin": "mean",
        "dir_cos": "mean",
        "intensidad_kt": "mean",
        "rafaga_kt": "max",
        "temperatura": "mean",
        "rocio": "mean",
    }
    available = {k: v for k, v in cols.items() if k in df.columns}
    df = df.resample("1h").agg(available)

    for col in ["dir_sin", "dir_cos", "intensidad_kt", "temperatura", "rocio"]:
        if col in df.columns:
            df[col] = df[col].interpolate(method="linear")

    if "rafaga_kt" in df.columns:
        df["rafaga_kt"] = df["rafaga_kt"].fillna(0)

    return df


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def build_feature_matrix(
    metar_strings: Optional[list[str]],
    scaler_X,
    airport_code: str = "SKBO",
) -> tuple[pd.DataFrame, str]:
    """
    Build scaled feature matrix ready for LSTM inference.

    Returns (df_scaled, data_source) where data_source is 'provided' or 'simfac_api'.
    Raises ValueError if fewer than N_BACK valid records are available.
    """
    if metar_strings:
        raw_df = _parse_metar_strings(metar_strings)
        source = "provided"
    else:
        raw_df = _fetch_simfac(airport_code, hours=_DEFAULT_LOOKBACK_HOURS)
        source = "simfac_api"

    df = _extract_features(raw_df)
    df = _resample_and_fill(df)

    df = df.dropna(subset=["dir_sin", "dir_cos", "intensidad_kt"])

    if len(df) < N_BACK:
        raise ValueError(
            f"Se necesitan al menos {N_BACK} registros horarios válidos. "
            f"Se obtuvieron {len(df)}. "
            f"{'Proporciona más observaciones METAR.' if metar_strings else 'La API de SIMFAC devolvió pocos datos; intenta aumentar el horizonte de descarga.'}"
        )

    # Scale using pre-trained scaler (transform only, never fit)
    feat_cols = [c for c in FEATURES_IN if c in df.columns]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        df[feat_cols] = scaler_X.transform(df[feat_cols])

    return df, source
