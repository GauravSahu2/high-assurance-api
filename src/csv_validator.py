import io
import pandas as pd
import pandera as pa
from pandera import Column, DataFrameSchema, Check

_INJECTION_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
MAX_ROWS = 10_000
MAX_FILE_BYTES = 5 * 1024 * 1024

DATASET_SCHEMA = DataFrameSchema(
    {
        "user_id": Column(
            str, 
            Check(lambda s: s.str.len() > 0, error="user_id must be non-empty"), 
            nullable=False
        ),
        "amount": Column(
            float, 
            [
                Check(lambda s: s >= 0, error="amount must be non-negative"), 
                Check(lambda s: s <= 1000000, error="amount exceeds cap")
            ], 
            nullable=False
        ),
        "description": Column(str, nullable=True, required=False),
    },
    strict=False,
    coerce=True,
)

def validate_and_sanitize_csv(raw_bytes: bytes) -> pd.DataFrame:
    if len(raw_bytes) > MAX_FILE_BYTES:
        raise ValueError(f"File too large (max {MAX_FILE_BYTES}).")
    
    try:
        df = pd.read_csv(io.BytesIO(raw_bytes), dtype=str, keep_default_na=False)
    except Exception as exc:
        raise ValueError(f"Failed to parse CSV: {exc}") from exc

    if df.empty or len(df.columns) == 0:
        raise ValueError("CSV is empty.")
    if len(df) > MAX_ROWS:
        raise ValueError(f"Too many rows (max {MAX_ROWS}).")

    # Sanitize ONLY non-numeric columns to preserve negative signs
    for col in df.columns:
        if col == "amount":
            continue
        df[col] = df[col].map(
            lambda x: str(x).lstrip("".join(_INJECTION_PREFIXES)) if pd.notna(x) else x
        )

    try:
        # Capture the dataframe so amounts are returned as actual floats
        df = DATASET_SCHEMA.validate(df, lazy=True)
    except pa.errors.SchemaErrors as exc:
        # Cast the complex Pandera error object to a string for the API response
        raise ValueError(f"Schema validation failed: {exc}")
    
    return df
