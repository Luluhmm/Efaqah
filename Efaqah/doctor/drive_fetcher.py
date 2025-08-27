# doctor/drive_fetcher.py
from pathlib import Path
import gdown

_HTML = (b"<!DOCTYPE html", b"<html", b"Google Drive", b"quota", b"Sign in")

def _looks_like_html(p: Path, head=4096) -> bool:
    try:
        with open(p, "rb") as f:
            return any(sig in f.read(head) for sig in _HTML)
    except Exception:
        return True

def download_if_missing(drive_id_or_url: str, dest_path: Path) -> Path:
    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    url = (drive_id_or_url if drive_id_or_url.startswith("http")
           else f"https://drive.google.com/uc?export=download&id={drive_id_or_url}")

    # fuzzy=True lets you pass share links like .../file/d/<ID>/view
    gdown.download(url, str(dest_path), quiet=False, fuzzy=True, use_cookies=False)

    # sanity checks (avoid saving HTML viewer page)
    if (not dest_path.exists()) or dest_path.stat().st_size < 1024 or _looks_like_html(dest_path):
        try: dest_path.unlink()
        except Exception: pass
        raise RuntimeError(
            "Google Drive download failed (HTML or tiny file). "
            "Make sure this is a FILE link/ID (not folder) and sharing is "
            "'Anyone with the link – Viewer', and quota not exceeded."
        )
    return dest_path
