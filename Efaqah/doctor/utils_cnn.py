# doctor/utils_cnn.py
import json, subprocess, os
from pathlib import Path
from django.conf import settings
from tempfile import NamedTemporaryFile
from .drive_fetcher import download_if_missing

TF_PY = Path(settings.BASE_DIR) / "venv_tf" / ("bin/python" if os.name != "nt" else "Scripts/python.exe")
RUNNER = Path(settings.BASE_DIR) / "cnn_runner.py"


CNN_DRIVE = "1fQ8ht1TwHMIyYvXVcKfn1csvK2VtIZAz"  

CNN_MODEL_PATH = Path(settings.MODEL_CACHE_DIR) / "trained_cnn_modelfinal96.keras"
download_if_missing(CNN_DRIVE, CNN_MODEL_PATH)

def cnn_predict_from_uploaded_file(django_file) -> tuple[float, int]:
    with NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        for chunk in django_file.chunks():
            tmp.write(chunk)
        tmp_path = tmp.name
    try:
        cmd = [str(TF_PY), str(RUNNER), str(CNN_MODEL_PATH), tmp_path]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)

        if proc.returncode != 0:
            try:
                payload = json.loads(proc.stdout.decode("utf-8", errors="ignore"))
                raise RuntimeError(f"CNN runner failed: {payload.get('error')}")
            except Exception:
                raise RuntimeError(f"CNN runner failed. Stderr: {proc.stderr.decode(errors='ignore')}")

        data = json.loads(proc.stdout.decode("utf-8", errors="ignore"))
        if "error" in data:
            raise RuntimeError(f"CNN error: {data['error']}")
        return float(data["prob"]), int(data["label"])
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass
