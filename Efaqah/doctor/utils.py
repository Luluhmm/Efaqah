# doctor/utils.py
from pathlib import Path
import json, joblib
import pandas as pd

APP_DIR    = Path(__file__).resolve().parent      
MODEL_DIR  = APP_DIR / "strokemodels"
MODEL_PATH = MODEL_DIR / "stroke_HGBC_pipeline92.pkl"
META_PATH  = MODEL_DIR / "stroke_HGBC_meta92.json"

try:
    PIPELINE   = joblib.load(MODEL_PATH)
    META       = json.loads(META_PATH.read_text())
    THRESHOLD  = float(META["threshold"])
    EXPECTED_COLS = META["expected_cols"]
except Exception as e:
    PIPELINE = None
    THRESHOLD = None
    EXPECTED_COLS = None
    raise RuntimeError(
        "Model not loaded.\n"
        f"Expected files:\n  {MODEL_PATH}\n  {META_PATH}\n"
        f"Reason: {type(e).__name__}: {e}"
    )

def predict_risk(payload: dict):
    if PIPELINE is None:
        raise RuntimeError("Model not loaded.")
    df = pd.DataFrame([payload])

    # validate columns + NaNs
    missing_cols = [c for c in EXPECTED_COLS if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required fields: {missing_cols}")

    df = df[EXPECTED_COLS]
    if df.isna().any().any():
        na_map = df.isna().iloc[0].to_dict()
        missing = [k for k, v in na_map.items() if v]
        raise ValueError(f"All fields are required. Missing: {missing}")

    proba = float(PIPELINE.predict_proba(df)[:, 1][0])
    label = int(proba >= THRESHOLD)
    return proba, label, THRESHOLD
