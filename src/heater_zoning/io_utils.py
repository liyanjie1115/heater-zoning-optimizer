from io import BytesIO
from pathlib import Path
from typing import Iterable

import pandas as pd


COLUMN_ALIASES = {
    "distance_mm": "distance_mm",
    "distance": "distance_mm",
    "x": "distance_mm",
    "位置": "distance_mm",
    "距离": "distance_mm",
    "距离_mm": "distance_mm",
    "temperature_c": "temperature_c",
    "temperature": "temperature_c",
    "temp": "temperature_c",
    "温度": "temperature_c",
    "温度_c": "temperature_c",
}


def _normalize_columns(columns: Iterable[str]):
    normalized = []
    for col in columns:
        key = str(col).strip().lower()
        normalized.append(COLUMN_ALIASES.get(key, str(col).strip()))
    return normalized


def normalize_profile_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        raise ValueError("输入数据为空。")

    renamed = df.copy()
    renamed.columns = _normalize_columns(renamed.columns)

    required = {"distance_mm", "temperature_c"}
    if not required.issubset(set(renamed.columns)):
        raise ValueError("输入数据需要包含 distance_mm 和 temperature_c 两列。")

    cleaned = renamed.loc[:, ["distance_mm", "temperature_c"]].copy()
    cleaned["distance_mm"] = pd.to_numeric(cleaned["distance_mm"], errors="coerce")
    cleaned["temperature_c"] = pd.to_numeric(cleaned["temperature_c"], errors="coerce")
    cleaned = cleaned.dropna().sort_values("distance_mm").drop_duplicates("distance_mm")

    if len(cleaned) < 2:
        raise ValueError("至少需要两行有效数据。")
    if (cleaned["distance_mm"].diff().fillna(1) <= 0).any():
        raise ValueError("距离列必须严格递增。")

    return cleaned.reset_index(drop=True)


def read_profile_upload(file_storage) -> pd.DataFrame:
    filename = file_storage.filename or ""
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    payload = file_storage.read()
    buffer = BytesIO(payload)

    if suffix == "csv":
        df = pd.read_csv(buffer)
    elif suffix in {"xlsx", "xls"}:
        df = pd.read_excel(buffer)
    else:
        raise ValueError("仅支持 CSV 或 Excel 文件。")

    return normalize_profile_dataframe(df)


def read_profile_file(file_path: str) -> pd.DataFrame:
    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        df = pd.read_csv(path)
    elif suffix in {".xlsx", ".xls"}:
        df = pd.read_excel(path)
    else:
        raise ValueError("仅支持 CSV 或 Excel 文件。")
    return normalize_profile_dataframe(df)

