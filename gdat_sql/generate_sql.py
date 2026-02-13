import zipfile
import os
import sys
import re
from io import BytesIO
from pathlib import Path
from typing import List, Tuple
import pandas as pd

SKIP_VALUES = ['(none)', 'valid_from_date', 'valid_to_date']
REQUIRED_COLUMNS = {
    'source_column': 'Source column name',
    'target_column': 'Column name',
    'source_table': 'Source table name',
    'data_type': 'Data type'
}
WORKDIR = Path.cwd() / "workdir"


def is_dim_or_ref_filename(file_name: str) -> bool:
    name = Path(file_name).stem.lower()
    return re.search(r'(^|[._\-/\s])(dim|ref)([._\-/\s]|$)', name) is not None


def get_column_mapping(file_bytes: bytes, file_name: str) -> List[Tuple[str, str, str, str]]:
    ext = Path(file_name).suffix.lower()
    engine = "openpyxl" if ext == ".xlsx" else ("xlrd" if ext == ".xls" else None)

    with BytesIO(file_bytes) as bio:
        df = pd.read_excel(bio, sheet_name=0, engine=engine)

    missing_columns = [c for c in REQUIRED_COLUMNS.values() if c not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns in {file_name}: {', '.join(missing_columns)}")

    mappings = []
    for _, row in df[REQUIRED_COLUMNS.values()].dropna(how='all').iterrows():
        source_col = str(row[REQUIRED_COLUMNS['source_column']]).strip()
        target_col = str(row[REQUIRED_COLUMNS['target_column']]).strip()
        source_table = str(row[REQUIRED_COLUMNS['source_table']]).strip()
        data_type = str(row[REQUIRED_COLUMNS['data_type']]).strip()

        if not source_col or not target_col or source_col in SKIP_VALUES:
            continue

        mappings.append((source_col, target_col, source_table, data_type))

    if not mappings:
        raise ValueError(f"No valid column mappings found in {file_name}")

    return mappings


def normalize_type(data_type: str) -> str:
    dt = data_type.lower()
    if "bigint" in dt or "big int" in dt:
        return "BIGINT"
    if "integer" in dt or re.search(r'\bint\b', dt):
        return "INT"
    if "varchar" in dt or "string" in dt or "text" in dt:
        return "STRING"
    if "datetime" in dt or "timestamp" in dt:
        return "TIMESTAMP"
    if dt == "date":
        return "DATE"
    return data_type


def generate_sql_query(mappings: List[Tuple[str, str, str, str]], file_name: str) -> str:
    select_lines = []
    source_table = mappings[0][2]

    for source_col, target_col, _, data_type in mappings:
        if "snapshot" in source_col.lower():
            src_expr = "curdate()"
            tgt_type = "DATE"
        else:
            src_expr = source_col.upper()
            tgt_type = normalize_type(data_type)

        select_lines.append(f"CAST({src_expr} AS {tgt_type}) AS {target_col}")

    select_lines.append("CAST(curdate() AS DATE) AS snapshot_date")

    if not is_dim_or_ref_filename(file_name):
        select_lines.append("CAST(null AS STRING) AS contract_cd")

    return "SELECT\n" + ",\n".join(select_lines) + "\nFROM\n" + source_table + "\n"


def process_archive(zip_path: Path, workdir: Path) -> None:
    base = zip_path.stem
    parent_dir = workdir / base
    parent_dir.mkdir(parents=True, exist_ok=True)

    raw_dir = parent_dir / "raw"
    out_dir = parent_dir / "sql"
    raw_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        excel_names = [n for n in zf.namelist() if n.lower().endswith((".xlsx", ".xls"))]
        if not excel_names:
            return

        for name in excel_names:
            try:
                zf.extract(name, path=raw_dir)
            except Exception:
                pass

        for name in excel_names:
            try:
                with zf.open(name) as f:
                    file_bytes = f.read()
                mappings = get_column_mapping(file_bytes, name)
                sql_query = generate_sql_query(mappings, Path(name).name)
            except Exception:
                continue

            file_stem = os.path.splitext(Path(name).name)[0]
            out_path = out_dir / f"{file_stem}.sql"

            try:
                with out_path.open("w", encoding="utf-8") as out:
                    out.write(sql_query)
            except Exception:
                pass


def main() -> int:
    if not WORKDIR.exists():
        return 2

    archives = sorted(WORKDIR.glob("*.zip"))
    if not archives:
        return 0

    for zip_path in archives:
        process_archive(zip_path, WORKDIR)

    return 0


if __name__ == "__main__":
    sys.exit(main())
