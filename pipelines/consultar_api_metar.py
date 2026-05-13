"""
Modulo para consultar METAR (Meteorological Aerodrome Report) desde la API de SIMFAC.

Permite obtener datos meteorologicos de aeropuertos colombianos usando
el codigo OACI, con filtro por rango de fechas. Los resultados pueden
exportarse a CSV para su uso en los pipelines de preprocesamiento.

Uso desde CLI:
    python pipelines/consultar_api_metar.py --oaci SKBO --start "2024-06-11" --end "2024-06-12"

Uso como modulo:
    from pipelines.consultar_api_metar import obtener_metar, metar_a_dataframe
    datos = obtener_metar("SKBO", 1718141683, 1718228083)
    df = metar_a_dataframe(datos)
"""

from __future__ import annotations

import argparse
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd


API_BASE_URL = "https://simfac.fac.mil.co/api/1.0/metaresForOacisForTimes"


def convertir_a_unix(fecha_str: str) -> int:
    """Convierte una fecha en formato ISO a timestamp Unix UTC.

    Args:
        fecha_str: Fecha en formato "YYYY-MM-DD" o "YYYY-MM-DD HH:MM".

    Returns:
        Timestamp Unix en segundos (int).
    """
    if " " in fecha_str:
        dt = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M")
    else:
        dt = datetime.strptime(fecha_str, "%Y-%m-%d")
    return int(dt.replace(tzinfo=timezone.utc).timestamp())


def obtener_metar(
    oaci: str,
    begin_date: int,
    end_date: int,
) -> dict:
    """Consulta la API de SIMFAC y retorna los METAR en el rango de fechas.

    Args:
        oaci: Codigo OACI del aeropuerto (ej. "SKBO", "SKBQ").
        begin_date: Timestamp Unix de inicio.
        end_date: Timestamp Unix de fin.

    Returns:
        Diccionario con la respuesta JSON de la API.

    Raises:
        urllib.error.HTTPError: Si la API responde con codigo de error.
        urllib.error.URLError: Si hay problemas de conexion.
        json.JSONDecodeError: Si la respuesta no es JSON valido.
    """
    url = f"{API_BASE_URL}?beginDate={begin_date}&endDate={end_date}&oacis={oaci}"
    print(f"Consultando: {oaci} desde {begin_date} hasta {end_date}")
    print(f"URL: {url}")

    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"Error HTTP {e.code}: {e.reason}")
        raise
    except urllib.error.URLError as e:
        print(f"Error de conexion: {e.reason}")
        raise
    except json.JSONDecodeError as e:
        print(f"Error al decodificar respuesta JSON: {e}")
        raise

    return data


def metar_a_dataframe(datos_api: dict) -> pd.DataFrame:
    """Convierte la respuesta JSON de la API en un DataFrame plano.

    Aplana la estructura anidada ``{oaci: [{Airport, OACI, METARES: [{Date, METAR}]}]}``
    en filas individuales por cada reporte METAR. Adiciona la columna
    ``FECHA_HORA_REPORTE`` como datetime.

    Args:
        datos_api: Diccionario devuelto por ``obtener_metar()``.

    Returns:
        DataFrame con columnas: OACI, Aeropuerto, Latitud, Longitud,
        Fecha, METAR, FECHA_HORA_REPORTE.
    """
    registros = []
    for oaci_key, aeropuertos in datos_api.items():
        for aeropuerto in aeropuertos:
            oaci = aeropuerto.get("OACI", oaci_key)
            airport = aeropuerto.get("Airport", "")
            latitud = aeropuerto.get("latitud", "")
            longitud = aeropuerto.get("longitude", "")
            for metar_entry in aeropuerto.get("METARES", []):
                registros.append(
                    {
                        "OACI": oaci,
                        "Aeropuerto": airport,
                        "Latitud": latitud,
                        "Longitud": longitud,
                        "Fecha": metar_entry.get("Date", ""),
                        "METAR": metar_entry.get("METAR", ""),
                    }
                )

    df = pd.DataFrame(registros)

    if not df.empty and "Fecha" in df.columns:
        df["FECHA_HORA_REPORTE"] = pd.to_datetime(
            df["Fecha"], format="%d-%m-%Y %H:%M:%S", errors="coerce"
        )

    return df


def guardar_csv(df: pd.DataFrame, ruta: Path) -> None:
    """Guarda el DataFrame como CSV, creando directorios si es necesario.

    Args:
        df: DataFrame con datos METAR.
        ruta: Ruta de salida del archivo CSV.
    """
    ruta.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ruta, index=False)
    print(f"Guardado: {ruta} ({len(df):,} registros)")


def consultar_metar(
    oaci: str = "SKBO",
    start: str | None = None,
    end: str | None = None,
    days: int | None = None,
    output: str | None = None,
) -> pd.DataFrame:
    """Consulta METAR y retorna un DataFrame.

    Args:
        oaci: Codigo OACI del aeropuerto.
        start: Fecha inicio (YYYY-MM-DD o 'YYYY-MM-DD HH:MM').
        end: Fecha fin (YYYY-MM-DD o 'YYYY-MM-DD HH:MM').
        days: Descargar ultimos N dias (alternativa a start/end).
        output: Ruta opcional para guardar CSV.

    Returns:
        DataFrame con los METAR obtenidos.
    """
    ahora = datetime.now(timezone.utc)

    if days is not None:
        begin = int((ahora - timedelta(days=days)).timestamp())
        end_ts = int(ahora.timestamp())
    elif start and end:
        begin = convertir_a_unix(start)
        end_ts = convertir_a_unix(end)
    else:
        begin = int((ahora - timedelta(days=7)).timestamp())
        end_ts = int(ahora.timestamp())
        print("Sin fechas especificadas. Usando ultimos 7 dias.")

    datos_api = obtener_metar(oaci, begin, end_ts)
    df = metar_a_dataframe(datos_api)

    if df.empty:
        print("No se encontraron registros METAR para los parametros dados.")
        return df

    if output:
        guardar_csv(df, Path(output))
    else:
        ruta = Path("data/NewData") / f"{oaci.lower()}.csv"
        guardar_csv(df, ruta)

    print(f"Registros obtenidos: {len(df):,}")
    print(
        f"Rango fechas: {df['FECHA_HORA_REPORTE'].min()} a {df['FECHA_HORA_REPORTE'].max()}"
    )

    return df


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Consulta METAR desde la API de SIMFAC y los exporta a CSV",
        epilog=(
            "Ejemplos:\n"
            "  %(prog)s --oaci SKBQ --start 2024-06-01 --end 2024-06-30\n"
            "  %(prog)s --oaci SKBO --days 14\n"
            "  %(prog)s --oaci SKBQ --days 7 --output data/raw/skbq_latest.csv\n"
            "  %(prog)s  (ultimos 7 dias, OACI por defecto SKBO)"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--oaci",
        default="SKBO",
        help="Codigo OACI del aeropuerto (default: SKBO)",
    )
    parser.add_argument(
        "--start",
        "--begin-date",
        dest="start",
        help="Fecha inicio (YYYY-MM-DD o 'YYYY-MM-DD HH:MM')",
    )
    parser.add_argument(
        "--end",
        "--end-date",
        dest="end",
        help="Fecha fin (YYYY-MM-DD o 'YYYY-MM-DD HH:MM')",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Descargar ultimos N dias (alternativa a --start/--end)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Ruta para guardar CSV (default: data/Processed/{oaci}_api.csv)",
    )

    args = parser.parse_args()
    consultar_metar(
        oaci=args.oaci,
        start=args.start,
        end=args.end,
        days=args.days,
        output=args.output,
    )


if __name__ == "__main__":
    main()
