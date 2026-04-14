import argparse
import os
import re
from pathlib import Path

import pandas as pd


def cargar_datos(ruta_csv: Path) -> pd.DataFrame:
    return pd.read_csv(ruta_csv)


def eliminar_registros_invalidos(df: pd.DataFrame) -> pd.DataFrame:
    registros_iniciales = len(df)
    invalid_count = df["TEXTO_REPORTE"].str.contains("NIL", na=False).sum()
    invalid_percent = (invalid_count / registros_iniciales) * 100

    print("=" * 60)
    print("ELIMINACION DE REGISTROS INVALIDOS")
    print("=" * 60)
    print(f"\n Registros iniciales: {registros_iniciales:,}")
    print(f" Registros invalidos (NIL): {invalid_count:,} ({invalid_percent:.2f}%)")

    df = df[~df["TEXTO_REPORTE"].str.contains("NIL", na=False)].copy()

    registros_validos = len(df)
    print(f" Registros validos despues de limpieza: {registros_validos:,}")
    print(f" Registros eliminados: {registros_iniciales - registros_validos:,}")
    print(f"\n Forma del dataset despues de limpieza: {df.shape}")

    return df


def normalizar_fechas(df: pd.DataFrame) -> pd.DataFrame:
    print("=" * 60)
    print("NORMALIZACION DE FECHAS")
    print("=" * 60)

    df["FECHA_HORA_REPORTE"] = pd.to_datetime(
        df["FECHA_REPORTE"].astype(str), errors="coerce"
    )

    fechas_invalidas = df["FECHA_HORA_REPORTE"].isna().sum()
    if fechas_invalidas > 0:
        print(f"  Advertencia: {fechas_invalidas} fechas no pudieron ser convertidas")

    print(" Columna FECHA_HORA_REPORTE creada")
    print(
        f"   Rango: {df['FECHA_HORA_REPORTE'].min()} a {df['FECHA_HORA_REPORTE'].max()}"
    )

    df["Año"] = df["FECHA_HORA_REPORTE"].dt.year
    df["Mes"] = df["FECHA_HORA_REPORTE"].dt.month
    df["Dia"] = df["FECHA_HORA_REPORTE"].dt.day
    df["Hora"] = df["FECHA_HORA_REPORTE"].dt.hour

    if df[df["Año"] == 1900].shape[0] > 0:
        registros_eliminados_fecha = len(df[df["Año"] == 1900])
        df = df[df["Año"] != 1900].copy()
        print(
            f" Eliminados {registros_eliminados_fecha} registros con fecha invalida (1900)"
        )

    print(f"\n Forma del dataset despues de normalizacion: {df.shape}")

    return df


def tokenizar_metar(df: pd.DataFrame) -> pd.DataFrame:
    df["tokens"] = df["TEXTO_REPORTE"].str.split()
    return df


def extraer_variables_meteorologicas(df: pd.DataFrame) -> pd.DataFrame:
    print("Extrayendo variables meteorologicas...")

    df["aerodromo"] = df["tokens"].str[0]
    df["fecha_zulu"] = df["tokens"].str[1]
    df["viento"] = df["tokens"].str[2]
    df["visibilidad"] = df["tokens"].str[3]

    df["temperatura/rocio"] = df["TEXTO_REPORTE"].str.extract(r"(\d{2}\/\d{2})")
    df["presion"] = df["TEXTO_REPORTE"].str.extract(r"(A\d{4})")
    df["nubosidad"] = (
        df["TEXTO_REPORTE"]
        .str.findall(r"(FEW\d{3}\w*|SCT\d{3}\w*|BKN\d{3}\w*|OVC\d{3}\w*)")
        .str.join(", ")
    )
    df["fenomenos"] = (
        df["TEXTO_REPORTE"]
        .str.findall(r"\b(TS|RA|SHRA|FG|BR|HZ|CB|VC\w+)\b")
        .str.join(", ")
    )

    return df


def extraer_direccion_viento(viento_str):
    if pd.isna(viento_str) or str(viento_str) == "":
        return None
    match = re.match(r"(\d{3})", str(viento_str))
    return int(match.group(1)) if match else None


def extraer_velocidad_viento(viento_str):
    if pd.isna(viento_str) or str(viento_str) == "":
        return None
    match = re.match(r"(?:VRB|(\d{3}))(\d{2})", str(viento_str))
    if match:
        return int(match.group(2))
    return None


def agregar_componentes_viento(df: pd.DataFrame) -> pd.DataFrame:
    df["direccion_viento"] = df["viento"].apply(extraer_direccion_viento)
    df["velocidad_viento"] = df["viento"].apply(extraer_velocidad_viento)
    return df


def crear_dataset_procesado(df: pd.DataFrame) -> pd.DataFrame:
    columnas_finales = [
        "FECHA_HORA_REPORTE",
        "aerodromo",
        "fecha_zulu",
        "viento",
        "visibilidad",
        "nubosidad",
        "temperatura/rocio",
        "presion",
        "fenomenos",
    ]

    columnas_derivadas = ["direccion_viento", "velocidad_viento"]
    for col in columnas_derivadas:
        if col in df.columns:
            columnas_finales.append(col)

    df_procesado = df[columnas_finales].copy()
    return df_procesado


def exportar_dataset(df: pd.DataFrame, ruta_exportacion: Path) -> None:
    print("=" * 70)
    print("EXPORTACION DEL DATASET PROCESADO")
    print("=" * 70)

    ruta_exportacion.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ruta_exportacion, index=False)

    print("\n Dataset exportado exitosamente")
    print(f"   Ruta: {ruta_exportacion}")
    print(f"   Forma: {df.shape[0]:,} registros x {df.shape[1]} columnas")
    print(
        f"   Tamano del archivo: {os.path.getsize(ruta_exportacion) / 1024**2:.2f} MB"
    )


def ejecutar_pipeline(ruta_entrada: Path, ruta_salida: Path) -> None:
    df_raw = cargar_datos(ruta_entrada)
    df_raw = eliminar_registros_invalidos(df_raw)
    df_raw = normalizar_fechas(df_raw)
    df_raw = tokenizar_metar(df_raw)
    df_raw = extraer_variables_meteorologicas(df_raw)
    df_raw = agregar_componentes_viento(df_raw)

    df_procesado = crear_dataset_procesado(df_raw)
    exportar_dataset(df_procesado, ruta_salida)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pipeline de preprocesamiento METAR basado en 02_preprocesamiento.ipynb"
    )
    parser.add_argument(
        "--input",
        default="data/raw/DATOS_CRUDOS.csv",
        help="Ruta del CSV crudo (default: data/raw/DATOS_CRUDOS.csv)",
    )
    parser.add_argument(
        "--output",
        default="data/raw/DATOS_PROCESADOS.csv",
        help="Ruta de salida del CSV procesado (default: data/raw/DATOS_PROCESADOS.csv)",
    )

    args = parser.parse_args()
    ejecutar_pipeline(Path(args.input), Path(args.output))


if __name__ == "__main__":
    main()
