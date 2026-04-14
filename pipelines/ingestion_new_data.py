from __future__ import annotations

import argparse
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import pandas as pd
from pandas.errors import ParserError


def ensure_directories(raw_dir: Path, new_data_dir: Path) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    new_data_dir.mkdir(parents=True, exist_ok=True)


def find_bad_lines(csv_path: Path, output_path: Path) -> int:
    bad_lines = []
    quotechar = '"'
    with csv_path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, start=1):
            if line.count(quotechar) % 2 != 0:
                bad_lines.append((line_number, line.rstrip("\n")))

    if bad_lines:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as output:
            output.write("line_number\tcontent\n")
            for line_number, content in bad_lines:
                output.write(f"{line_number}\t{content}\n")

    return len(bad_lines)


def read_new_data(new_path: Path) -> pd.DataFrame:
    if new_path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(new_path)
    return pd.read_csv(new_path, sep=";", engine="python")


def load_data(raw_path: Path, new_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not raw_path.exists():
        raise FileNotFoundError(f"No se encuentra el archivo base: {raw_path}")

    if not new_path.exists():
        raise FileNotFoundError(
            f"No se encuentra el archivo de nuevos datos: {new_path}"
        )

    df_raw = pd.read_csv(raw_path)
    try:
        df_new = read_new_data(new_path)
    except ParserError as exc:
        bad_lines_path = new_path.with_suffix(".bad_lines.txt")
        bad_lines_count = find_bad_lines(new_path, bad_lines_path)
        message = (
            f"Error al leer {new_path}. Lineas sospechosas: {bad_lines_count}. "
            f"Detalle en: {bad_lines_path}"
        )
        raise ParserError(message) from exc
    return df_raw, df_new


def validate_columns(df_raw: pd.DataFrame, df_new: pd.DataFrame) -> None:
    if list(df_raw.columns) != list(df_new.columns):
        raise ValueError(
            "Las columnas del archivo nuevo no coinciden con el dataset original."
        )


def combine_datasets(df_raw: pd.DataFrame, df_new: pd.DataFrame) -> pd.DataFrame:
    df_combined = pd.concat([df_raw, df_new], ignore_index=True)
    before_dedup = len(df_combined)
    required_columns = ["FECHA_REPORTE", "HORA_REPORTE", "TIPO_REPORTE"]
    missing_columns = [
        col for col in required_columns if col not in df_combined.columns
    ]
    if missing_columns:
        raise ValueError(
            "Faltan columnas requeridas para deduplicar: " + ", ".join(missing_columns)
        )
    df_combined = df_combined.drop_duplicates(subset=required_columns, keep="first")
    after_dedup = len(df_combined)
    print(f"Registros antes de deduplicar: {before_dedup:,}")
    print(f"Registros despues de deduplicar: {after_dedup:,}")

    if "FECHA_REPORTE" in df_combined.columns:
        df_combined = df_combined.sort_values(by="FECHA_REPORTE")

    return df_combined


def backup_file(raw_path: Path, backup_dir: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"DATOS_CRUDOS_backup_{timestamp}.csv"
    shutil.copy2(raw_path, backup_path)
    return backup_path


def save_dataset(df: pd.DataFrame, raw_path: Path) -> None:
    df.to_csv(raw_path, index=False)


def dvc_add(path: Path) -> None:
    result = subprocess.run(["dvc", "add", str(path)], capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.returncode != 0:
        if result.stderr:
            print(result.stderr)
        raise RuntimeError("Fallo al ejecutar dvc add")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingesta de nuevos datos METAR y versionado con DVC"
    )
    parser.add_argument(
        "--raw",
        default="data/raw/DATOS_CRUDOS.csv",
        help="Ruta del dataset principal (default: data/raw/DATOS_CRUDOS.csv)",
    )
    parser.add_argument(
        "--new",
        default="data/NewData/skbo.csv",
        help="Ruta del archivo con nuevos datos (default: data/NewData/skbo.csv)",
    )
    parser.add_argument(
        "--backup-dir",
        default="data/raw",
        help="Directorio para respaldos (default: data/raw)",
    )
    args = parser.parse_args()

    project_root = Path(".").resolve()
    raw_path = (project_root / args.raw).resolve()
    new_path = (project_root / args.new).resolve()
    backup_dir = (project_root / args.backup_dir).resolve()

    raw_dir = raw_path.parent
    new_data_dir = new_path.parent

    ensure_directories(raw_dir, new_data_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)

    print(f"RAW_DATA_PATH: {raw_path}")
    print(f"NEW_DATA_PATH: {new_path}")

    df_raw, df_new = load_data(raw_path, new_path)
    print("Dataset original:", df_raw.shape)
    print("Dataset nuevo:", df_new.shape)

    validate_columns(df_raw, df_new)
    df_combined = combine_datasets(df_raw, df_new)

    backup_path = backup_file(raw_path, backup_dir)
    print(f"Backup creado: {backup_path}")

    save_dataset(df_combined, raw_path)
    print(f"Dataset actualizado: {raw_path}")

    dvc_add(raw_path)
    print("Listo. Recuerda hacer git add del .dvc y git commit.")


if __name__ == "__main__":
    main()
