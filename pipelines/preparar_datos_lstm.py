#!/usr/bin/env python3
"""
Pipeline completo de preparación de datos para LSTM.
Replica exactamente las transformaciones del notebook api_metar.ipynb.

Entrada: CSV crudo con columnas METAR (ej. skbo_ventana.csv)
Salida : CSV listo para entrenamiento + scalers .pkl
"""

import argparse
import pickle
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler


def cargar_datos(ruta: Path) -> pd.DataFrame:
    df = pd.read_csv(ruta)
    print(f"Dataset cargado: {df.shape}")
    return df


def eliminar_registros_nil(df: pd.DataFrame) -> pd.DataFrame:
    total = len(df)
    invalid = df["METAR"].str.contains("NIL", na=False).sum()
    print(f"Registros NIL: {invalid} ({invalid / total * 100:.2f}%)")
    df = df[~df["METAR"].str.contains("NIL", na=False)].copy()
    print(f"Registros válidos: {len(df)} (eliminados: {total - len(df)})")
    return df


def normalizar_fechas(df: pd.DataFrame) -> pd.DataFrame:
    df["FECHA_HORA_REPORTE"] = pd.to_datetime(
        df["FECHA_HORA_REPORTE"].astype(str), errors="coerce"
    )
    invalidas = df["FECHA_HORA_REPORTE"].isna().sum()
    if invalidas:
        print(f"  Advertencia: {invalidas} fechas inválidas")

    df["Año"] = df["FECHA_HORA_REPORTE"].dt.year
    df["Mes"] = df["FECHA_HORA_REPORTE"].dt.month
    df["Dia"] = df["FECHA_HORA_REPORTE"].dt.day
    df["Hora"] = df["FECHA_HORA_REPORTE"].dt.hour

    if (df["Año"] == 1900).any():
        n = (df["Año"] == 1900).sum()
        df = df[df["Año"] != 1900].copy()
        print(f"  Eliminados {n} registros con año 1900")

    print(
        f"  Rango: {df['FECHA_HORA_REPORTE'].min()} a {df['FECHA_HORA_REPORTE'].max()}"
    )
    return df


def tokenizar_y_limpiar_metar(df: pd.DataFrame) -> pd.DataFrame:
    patron_auto = r"\bAUTO\b\s?"
    df["TEXTO_REPORTE_CLEAN"] = (
        df["METAR"]
        .str.replace(patron_auto, "", regex=True, flags=re.IGNORECASE)
        .str.strip()
    )
    df["tokens"] = df["TEXTO_REPORTE_CLEAN"].str.split()
    print(f"  Tokens de ejemplo: {df['tokens'].iloc[0][:5]}")

    df = df[df["tokens"].str[0].str.len() == 4].copy()
    print(f"  Después de limpiar aeródromo: {len(df)}")

    df = df[df["tokens"].str[1].str.len().isin([6, 7])].copy()
    print(f"  Después de limpiar hora: {len(df)}")

    df = df[df["tokens"].str[2].str.len().isin([6, 7, 8, 9, 10])].copy()
    print(f"  Después de limpiar viento: {len(df)}")
    return df


def extraer_variables(df: pd.DataFrame) -> pd.DataFrame:
    df["viento"] = df["tokens"].str[2]
    print(f"  Columna 'viento' extraída de tokens[2]")

    def buscar_temp_rocio(tokens_list):
        if tokens_list is None:
            return np.nan
        if isinstance(tokens_list, str):
            tokens_list = [tokens_list]
        elif not isinstance(tokens_list, (list, tuple, np.ndarray)):
            return np.nan
        if len(tokens_list) == 0:
            return np.nan

        for token in tokens_list:
            if token is not None:
                token_str = str(token).strip()
                patron_con_barra = r"(\d{1,3}(?:\.\d+)?)\s*/\s*(\d{1,3}(?:\.\d+)?)"
                match = re.search(patron_con_barra, token_str)
                if match:
                    return f"{match.group(1)}/{match.group(2)}"
        return np.nan

    df["temperatura_rocio"] = df["tokens"].apply(buscar_temp_rocio)
    df["temperatura"] = df["temperatura_rocio"].str.split("/").str[0]
    df["rocio"] = df["temperatura_rocio"].str.split("/").str[1]
    print(
        f"  Temperatura/Rocío extraídos. Nulos temperatura: {df['temperatura'].isna().sum()}"
    )
    return df


def seleccionar_columnas_base(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "FECHA_HORA_REPORTE",
        "METAR",
        "Año",
        "Mes",
        "Dia",
        "Hora",
        "viento",
        "temperatura",
        "rocio",
    ]
    df = df[[c for c in cols if c in df.columns]].copy()
    print(f"  Columnas base: {list(df.columns)}")
    return df


def procesar_viento(df: pd.DataFrame) -> pd.DataFrame:
    df["FECHA_REPORTE"] = pd.to_datetime(df["FECHA_HORA_REPORTE"])
    df.set_index("FECHA_REPORTE", inplace=True)
    df.drop(columns=["Año", "Mes", "Dia", "Hora"], inplace=True, errors="ignore")

    df = df[df["viento"].notna()].copy()
    print(f"  Después de eliminar nulos en viento: {len(df)}")

    df["viento"] = df["viento"].str.replace(r"[A-Za-z]{3}$", "KT", regex=True)

    def parse_viento(cadena):
        if pd.isna(cadena) or not isinstance(cadena, str):
            return pd.Series([None, None, None])
        patron = r"^(\d{3}|VRB)(\d{2,3})(G\d{2,3})?KT$"
        m = re.match(patron, cadena)
        if m:
            direccion = float(m.group(1)) if m.group(1) != "VRB" else None
            velocidad = float(m.group(2))
            rafaga = float(m.group(3)[1:]) if m.group(3) else 0.0
            return pd.Series([direccion, velocidad, rafaga])
        return pd.Series([None, None, None])

    df[["direccion", "intensidad_kt", "rafaga_kt"]] = df["viento"].apply(parse_viento)

    df["direccion"] = df["direccion"].ffill()
    df = df[df["viento"].str.len() > 6].copy()
    df = df[df["intensidad_kt"].notnull()].copy()
    df = df[df["direccion"] <= 360].copy()
    print(f"  Después de filtros de viento: {len(df)}")

    umbral_maximo = 40
    df.loc[df["intensidad_kt"] > umbral_maximo, "intensidad_kt"] = np.nan
    print(f"  Capping intensidad > {umbral_maximo} kt aplicado")

    df.index = df.index.round("h")
    df = df[~df.index.duplicated(keep="last")].copy()
    print(f"  Después de redondear y deduplicar: {len(df)}")

    df["dir_sin"] = np.sin(np.radians(df["direccion"]))
    df["dir_cos"] = np.cos(np.radians(df["direccion"]))
    df["intensidad_log"] = np.log1p(df["intensidad_kt"])
    return df


def resamplear_e_interpolar(df: pd.DataFrame) -> pd.DataFrame:
    cols_numericas = [
        "dir_sin",
        "dir_cos",
        "intensidad_log",
        "rafaga_kt",
        "temperatura",
        "rocio",
    ]
    for col in cols_numericas:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    reglas = {
        "dir_sin": "mean",
        "dir_cos": "mean",
        "intensidad_log": "mean",
        "rafaga_kt": "max",
        "temperatura": "mean",
        "rocio": "mean",
    }
    reglas = {k: v for k, v in reglas.items() if k in df.columns}
    df = df.resample("1h").agg(reglas)

    for col in ["dir_sin", "dir_cos", "intensidad_log", "temperatura", "rocio"]:
        if col in df.columns:
            df[col] = df[col].interpolate(method="linear")

    if "rafaga_kt" in df.columns:
        df["rafaga_kt"] = df["rafaga_kt"].fillna(0)

    df = df.asfreq("h")
    print(f"  Valores nulos por columna:\n{df.isnull().sum()}")
    print(f"  Frecuencia: {df.index.freq}")
    return df


def normalizar_con_scaler(df: pd.DataFrame, ruta_scaler_base: Path) -> None:
    features_modelo = ["dir_sin", "dir_cos", "intensidad_log", "temperatura", "rocio"]
    targets = ["dir_sin", "dir_cos", "intensidad_log"]

    scaler_X = StandardScaler()
    df[features_modelo] = scaler_X.fit_transform(df[features_modelo])

    scaler_y = StandardScaler()
    df[targets] = scaler_y.fit_transform(df[targets])

    # Guardar scalers para uso en predicción
    ruta_scaler_base.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta_scaler_base.with_name("scaler_X.pkl"), "wb") as f:
        pickle.dump(scaler_X, f)
    with open(ruta_scaler_base.with_name("scaler_y.pkl"), "wb") as f:
        pickle.dump(scaler_y, f)

    print("  Normalización con StandardScaler aplicada")
    print(f"  scaler_X guardado: {ruta_scaler_base.with_name('scaler_X.pkl')}")
    print(f"  scaler_y guardado: {ruta_scaler_base.with_name('scaler_y.pkl')}")


def exportar_dataset(df: pd.DataFrame, ruta_csv: Path) -> None:
    ruta_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ruta_csv, index=True)
    print(
        f"  CSV exportado: {ruta_csv} ({df.shape[0]} registros x {df.shape[1]} columnas)"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline completo de preparación de datos LSTM (replica api_metar.ipynb)"
    )
    parser.add_argument(
        "--input",
        default="data/Processed/skbo_ventana.csv",
        help="Ruta del CSV crudo con METAR (default: data/Processed/skbo_ventana.csv)",
    )
    parser.add_argument(
        "--output",
        default="data/Processed/skbo_ventana_transformada.csv",
        help="Ruta del CSV transformado (default: data/Processed/skbo_ventana_transformada.csv)",
    )
    args = parser.parse_args()

    ruta_entrada = Path(args.input).resolve()
    ruta_salida = Path(args.output).resolve()

    print("=" * 60)
    print("PIPELINE COMPLETO DE PREPARACIÓN DE DATOS LSTM")
    print("=" * 60)
    print(f"INPUT : {ruta_entrada}")
    print(f"OUTPUT: {ruta_salida}")

    print("\n[1/8] Cargando datos...")
    df = cargar_datos(ruta_entrada)

    print("\n[2/8] Eliminando registros NIL...")
    df = eliminar_registros_nil(df)

    print("\n[3/8] Normalizando fechas...")
    df = normalizar_fechas(df)

    print("\n[4/8] Tokenizando y limpiando METAR...")
    df = tokenizar_y_limpiar_metar(df)

    print("\n[5/8] Extrayendo temperatura y rocío...")
    df = extraer_variables(df)

    print("\n[6/8] Seleccionando columnas base...")
    df = seleccionar_columnas_base(df)

    print("\n[7/8] Procesando viento (parse, componentes, resample)...")
    df = procesar_viento(df)
    df = resamplear_e_interpolar(df)

    print("\n[8/8] Normalizando con StandardScaler y exportando...")
    normalizar_con_scaler(df, ruta_salida)
    exportar_dataset(df, ruta_salida)

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETADO EXITOSAMENTE")
    print("=" * 60)


if __name__ == "__main__":
    main()
