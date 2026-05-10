"""
Descarga una ventana de horas hacia atras desde una fecha fin.

Re-usa las funciones de consultar_api_metar.py para obtener METAR
en un rango que va desde (end - hours) hasta end.

Uso:
    python pipelines/ventana_metar.py --oaci SKBQ --end "2024-06-30 12:00" --hours 50
    python pipelines/ventana_metar.py --oaci SKBO --hours 24
    python pipelines/ventana_metar.py  (ultimas 50 horas desde ahora, OACI=SKBO)
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pandas as pd

try:
    from consultar_api_metar import (
        convertir_a_unix,
        obtener_metar,
        metar_a_dataframe,
        guardar_csv,
    )
except ImportError:
    from pipelines.consultar_api_metar import (
        convertir_a_unix,
        obtener_metar,
        metar_a_dataframe,
        guardar_csv,
    )


def descargar_ventana(
    oaci: str = "SKBO",
    end: str | None = None,
    hours: int = 50,
    output: str | None = None,
) -> pd.DataFrame:
    """Descarga METAR en una ventana de horas hacia atras y retorna un DataFrame.

    Args:
        oaci: Codigo OACI del aeropuerto.
        end: Fecha fin (YYYY-MM-DD o 'YYYY-MM-DD HH:MM'). Default: ahora UTC.
        hours: Horas hacia atras desde la fecha fin.
        output: Ruta opcional para guardar CSV.

    Returns:
        DataFrame con los METAR obtenidos.
    """
    ahora = datetime.now(timezone.utc)

    if end:
        end_dt = (
            datetime.strptime(end, "%Y-%m-%d %H:%M")
            if " " in end
            else datetime.strptime(end, "%Y-%m-%d")
        )
        end_dt = end_dt.replace(tzinfo=timezone.utc)
    else:
        end_dt = ahora

    begin_dt = end_dt - timedelta(hours=hours)

    begin_ts = int(begin_dt.timestamp())
    end_ts = int(end_dt.timestamp())

    print(f"Ventana: {hours}h desde {begin_dt} hasta {end_dt}")

    datos_api = obtener_metar(oaci, begin_ts, end_ts)
    df = metar_a_dataframe(datos_api)

    if df.empty:
        print("No se encontraron registros METAR en la ventana solicitada.")
        return df

    if output:
        output_path = Path(output)
    else:
        output_path = Path("data/NewData") / f"{oaci.lower()}_ventana.csv"

    guardar_csv(df, output_path)
    print(f"Registros obtenidos: {len(df):,}")
    print(
        f"Rango fechas: {df['FECHA_HORA_REPORTE'].min()} a {df['FECHA_HORA_REPORTE'].max()}"
    )

    return df


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Descarga una ventana de METAR desde (fin - horas) hasta fin",
        epilog=(
            "Ejemplos:\n"
            "  %(prog)s --oaci SKBQ --end 2024-06-30 --hours 50\n"
            "  %(prog)s --oaci SKBO --hours 24\n"
            "  %(prog)s --oaci SKBQ --end '2024-06-30 12:00' --output data/raw/skbq_ventana.csv\n"
            "  %(prog)s  (ultimas 50 horas, OACI=SKBO)"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--oaci",
        default="SKBO",
        help="Codigo OACI del aeropuerto (default: SKBO)",
    )
    parser.add_argument(
        "--end",
        "--end-date",
        dest="end",
        default=None,
        help="Fecha fin (YYYY-MM-DD o 'YYYY-MM-DD HH:MM'). Default: ahora UTC",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=50,
        help="Horas hacia atras desde la fecha fin (default: 50)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Ruta para guardar CSV (default: data/NewData/{oaci}_ventana.csv)",
    )

    args = parser.parse_args()
    descargar_ventana(
        oaci=args.oaci,
        end=args.end,
        hours=args.hours,
        output=args.output,
    )


if __name__ == "__main__":
    main()
