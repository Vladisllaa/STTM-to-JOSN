import zipfile, json, os, re, sys
from io import BytesIO
from pathlib import Path
from typing import List, Tuple
import pandas as pd

WORKDIR = Path.cwd() / "workdir"
SKIP_VALUES = ['(none)', 'valid_from_date', 'valid_to_date']
REQUIRED_COLUMNS = {
    'name_column': 'Column name',
    'type_column': 'Data type',
    'mandatory_column': 'Mandatory field',
    'scd_type_1_column': 'SCD Type 1',
    'scd_type_2_column': 'SCD Type 2',
    'security_classification_column': 'Security Classification',
    'isBusinessKey': 'Business Key',
}
BUSINESS_DOMAIN = 'OTHERTEMP'
CLUSTER_NAME = 'gdp2-lakehouse-compute'
BASE_NOTEBOOK_DIR = "/Workspace/Shared/Data Platform"
MAIN_GROUP = "COINS_INGEST"
DEBUG_GROUP = "DEBUG_COINS_INGEST"


def safe_entity_code(name: str) -> str:
    code = re.sub(r"[^A-Za-z0-9]+", "_", name)
    return code.strip("_").upper()


def is_fact(file_stem: str) -> bool:
    return not re.search(r'(^|[._\-/\s])(dim|ref)([._\-/\s]|$)', file_stem.lower())


def create_sk_column(entity_name: str) -> dict:
    return {
        "columnName": f"{entity_name}_key",
        "typeName": "bigint",
        "isNullable": False,
        "isPrimaryKey": True,
        "isBusinessKey": False,
        "isType1SCD": False,
        "isType2SCD": False,
        "securityClassification": "Internal",
    }


def append_type_length(col: dict, col_spec: dict) -> None:
    if col['type'] == 'varchar':
        col_spec['typeLength'] = col.get('length', 255)
    elif col['type'] == 'decimal':
        col_spec['typePrecision'] = col.get('precision', 18)
        col_spec['typeScale'] = col.get('scale', 2)


def create_default_column(col: dict, i: int) -> dict:
    default_column = {
        "columnName": col['name'],
        "typeName": col['type'],
        "isNullable": col['mandatory'] != 'mandatory',
        "isPrimaryKey": False,
        "isBusinessKey": col['isBusinessKey'] == '1.0',
        "isType1SCD": col['scd_type_1'] == 'yes' and i > 2 and col['isBusinessKey'] != '1.0',
        "isType2SCD": col['scd_type_2'] == 'yes' and i > 2 and col['isBusinessKey'] != '1.0',
        "securityClassification": col['security_classification']
    }
    append_type_length(col, default_column)
    return default_column


def create_snapshot_date_column(file_stem: str) -> dict:
    return {
        "columnName": "snapshot_date",
        "typeName": "date",
        "isNullable": True,
        "isPrimaryKey": False,
        "isBusinessKey": False,
        "isType1SCD": is_fact(file_stem),
        "isType2SCD": False,
        "securityClassification": "Internal"
    }


def create_contract_cd_column(file_stem: str) -> dict:
    return {
        "columnName": "contract_cd",
        "typeName": "string",
        "isBusinessKey": False,
        "isPrimaryKey": False,
        "isType1SCD": is_fact(file_stem),
        "isType2SCD": False,
        "isNullable": True,
        "securityClassification": "Internal"
    }


def create_contract(entity_code: str, entity_name: str, description: str, destinationSchema: str,
                    main_group: str, debug_group: str, cluster_name: str, notebook_path: str,
                    business_domain: str, dependency: str) -> dict:
    return {
        "entityCode": entity_code,
        "entityName": entity_name,
        "entityDescription": description,
        "destinationSchema": destinationSchema,
        "isEnabled": True,
        "ingestionGroups": [main_group],
        "debugIngestionGroups": [debug_group],
        # "loadMethod": "snapshot",
        # "snapshotInterval": "daily",
        "clusterName": cluster_name,
        "notebookPath": notebook_path,
        "businessDomain": business_domain,
        "failIfSingleInvalidDetected": False,
        "dependencies": [dependency],
        "columns": [],
    }


def get_schema_type(file_bytes: bytes, file_name: str) -> str:
    ext = Path(file_name).suffix.lower()
    engine = "openpyxl" if ext == ".xlsx" else ("xlrd" if ext == ".xls" else None)

    with BytesIO(file_bytes) as bio:
        df = pd.read_excel(bio, sheet_name=0, engine=engine)
        if 'Target Schema' not in df.columns:
            raise ValueError(f"'Target Schema' column not found in {file_name}")
        if df['Target Schema'].astype(str).str.contains('gold', case=False).any():
            return "gold"
        return "silver"


def infer_columns_from_excel(file_bytes: bytes, file_name: str) -> List[dict]:
    ext = Path(file_name).suffix.lower()
    engine = "openpyxl" if ext == ".xlsx" else ("xlrd" if ext == ".xls" else None)

    with BytesIO(file_bytes) as bio:
        df = pd.read_excel(bio, sheet_name=0, engine=engine)

    missing_columns = [col for col in REQUIRED_COLUMNS.values() if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns in {file_name}: {', '.join(missing_columns)}")

    columns = []
    for _, row in df[REQUIRED_COLUMNS.values()].dropna(how='all').iterrows():
        col_name = str(row[REQUIRED_COLUMNS.get('name_column')]).strip()
        col_type = str(row[REQUIRED_COLUMNS.get('type_column')]).strip().lower()
        col_mandatory = str(row[REQUIRED_COLUMNS.get('mandatory_column')]).strip().lower()
        col_scd_type_1 = str(row[REQUIRED_COLUMNS.get('scd_type_1_column')]).strip().lower()
        col_scd_type_2 = str(row[REQUIRED_COLUMNS.get('scd_type_2_column')]).strip().lower()
        col_security_classification = str(row[REQUIRED_COLUMNS.get('security_classification_column')]).strip()
        col_business_key = str(row[REQUIRED_COLUMNS.get('isBusinessKey')]).strip()

        if not col_name or col_name in SKIP_VALUES:
            continue

        col_info = {
            'name': col_name,
            'type': col_type,
            'length': 255,
            'mandatory': col_mandatory,
            'scd_type_1': col_scd_type_1,
            'scd_type_2': col_scd_type_2,
            'security_classification': col_security_classification,
            'isBusinessKey': col_business_key
        }

        if 'varchar' in col_type and '(' in col_type:
            length = int(col_type.split('(')[1].split(')')[0])
            col_info.update({'length': length})
            col_info['type'] = 'varchar'
        elif 'decimal' in col_type and '(' in col_type:
            parts = col_type.split('(')[1].split(')')[0].split(',')
            precision = int(parts[0].strip())
            scale = int(parts[1].strip()) if len(parts) > 1 else 0
            col_info.update({'precision': precision, 'scale': scale})
            col_info['type'] = 'decimal'

        columns.append(col_info)

    if not columns:
        raise ValueError(f"No valid column definitions found in {file_name}")

    return columns


def detect_segment_and_dependency(entity_name: str) -> Tuple[str, str]:
    tokens = entity_name.lower().split("_")
    segment = "GEN"
    if "sph" in tokens:
        segment = "SPH"
    elif "cm" in tokens:
        segment = "CM"
    dependency = ''
    return segment, dependency


def build_silver_contract(file_stem: str, columns: List[dict], business_domain: str,
                         cluster_name: str, base_notebook_dir: str) -> dict:
    entity_name = file_stem
    entity_code = 'SILVER_' + safe_entity_code(file_stem)
    description = f"The silver_{business_domain.lower()}.{entity_name} experience table."
    destinationSchema = f"SILVER_{business_domain}"

    _, dependency = detect_segment_and_dependency(entity_name)
    main_group = "DPM_INGEST"
    debug_group = "DEBUG_DPM_INGEST"
    notebook_path = f"{base_notebook_dir}/{business_domain}/transform_{entity_name}"

    contract = create_contract(entity_code, entity_name, description, destinationSchema,
                               main_group, debug_group, cluster_name, notebook_path,
                               business_domain, dependency)

    contract["columns"].append(create_sk_column(entity_name))

    for i, col in enumerate(columns, start=2):
        contract["columns"].append(create_default_column(col, i))

    contract["columns"].append(create_snapshot_date_column(file_stem))
    if is_fact(file_stem):
        contract["columns"].append(create_contract_cd_column(file_stem))

    return contract


def build_gold_contract(file_stem: str, columns: List[dict], business_domain: str,
                        cluster_name: str, base_notebook_dir: str) -> dict:
    entity_name = file_stem
    code_prefix = 'DIM' if re.search(r'(^|[._\-/\s])dim([._\-/\s]|$)', file_stem.lower()) else 'FCT'
    entity_code = f"{code_prefix}_{business_domain}_{entity_name}".upper()
    description = f"The gold_{business_domain.lower()}.{entity_name} experience table."
    destinationSchema = f"GOLD_{business_domain}"

    _, dependency = detect_segment_and_dependency(entity_name)
    main_group = MAIN_GROUP
    debug_group = DEBUG_GROUP
    notebook_path = f"{base_notebook_dir}/{business_domain}/transform_{entity_name}"

    contract = create_contract(entity_code, entity_name, description, destinationSchema,
                               main_group, debug_group, cluster_name, notebook_path,
                               business_domain, dependency)

    contract["columns"].append(create_sk_column(entity_name))

    for i, col in enumerate(columns, start=2):
        if col.get('name') == '_snapshot_date_key':
            continue
        contract["columns"].append(create_default_column(col, i))

    contract["columns"].append(create_snapshot_date_column(file_stem))
    if is_fact(file_stem):
        contract["columns"].append(create_contract_cd_column(file_stem))

    return contract


def process_archive(zip_path: Path, workdir: Path, business_domain: str,
                    cluster_name: str, base_notebook_dir: str) -> None:
    base = zip_path.stem
    parent_dir = workdir / base
    parent_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = parent_dir / "raw"
    out_dir = parent_dir / "contracts"
    raw_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        excel_names = [n for n in zf.namelist() if n.lower().endswith((".xlsx", ".xls"))]
        if not excel_names:
            print(f"[WARN] No .xlsx/.xls files found in {zip_path.name}")
            return

        for name in excel_names:
            try:
                zf.extract(name, path=raw_dir)
            except Exception as e:
                print(f"[WARN] Failed to extract {name} from {zip_path.name}: {e}")

        for name in excel_names:
            try:
                with zf.open(name) as f:
                    file_bytes = f.read()
                columns = infer_columns_from_excel(file_bytes, name)
                schema_type = get_schema_type(file_bytes, name)
            except Exception as e:
                print(f"[ERROR] Failed to read columns from {zip_path.name}:{name} -> {e}")
                continue

            file_stem = os.path.splitext(Path(name).name)[0]
            if schema_type == "gold":
                contract = build_gold_contract(file_stem, columns, business_domain, cluster_name, base_notebook_dir + '/GOLD')
            else:
                contract = build_silver_contract(file_stem, columns, business_domain, cluster_name, base_notebook_dir + '/SILVER')

            out_path = out_dir / f"{file_stem}.json"

            try:
                with out_path.open("w", encoding="utf-8") as out:
                    json.dump(contract, out, ensure_ascii=False, indent=2)
                print(f"[OK] Wrote {out_path}")
            except Exception as e:
                print(f"[ERROR] Failed to write contract {out_path}: {e}")


def main() -> int:
    if not WORKDIR.exists():
        print(f"[ERROR] workdir does not exist: {WORKDIR}")
        return 2

    archives = sorted(WORKDIR.glob("*.zip"))
    if not archives:
        print(f"[WARN] No .zip archives found under {WORKDIR}")
        return 0

    print(f"[INFO] Found {len(archives)} archive(s) under {WORKDIR}")
    for zip_path in archives:
        print(f"[INFO] Processing {zip_path.name}")
        process_archive(zip_path, WORKDIR, BUSINESS_DOMAIN, CLUSTER_NAME, BASE_NOTEBOOK_DIR)

    print("[DONE] Contract generation complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
