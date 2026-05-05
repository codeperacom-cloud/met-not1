import json
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import current_app


def license_path() -> Path:
    path = Path(current_app.instance_path)
    path.mkdir(parents=True, exist_ok=True)
    return path / "license.json"


def read_license() -> dict:
    path = license_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def license_status() -> dict:
    record = read_license()
    end_date = record.get("end_date")
    if not end_date:
        return {"valid": False, "reason": "Lisans bulunamadi.", "license": record}

    today = date.today()
    try:
        expires = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        return {"valid": False, "reason": "Lisans tarihi gecersiz.", "license": record}

    if today > expires:
        return {"valid": False, "reason": "Lisans suresi doldu.", "license": record}
    return {"valid": True, "reason": "Lisans aktif.", "license": record, "days_left": (expires - today).days}


def save_license(key: str, period: str) -> dict:
    key = (key or "").strip()
    if len(key) < 8:
        raise ValueError("Lisans anahtari en az 8 karakter olmali.")

    today = date.today()
    if period == "monthly":
        end = today + timedelta(days=30)
    elif period == "yearly":
        end = today + timedelta(days=365)
    else:
        raise ValueError("Lisans periyodu aylik veya yillik olmali.")

    record = {
        "key": key,
        "period": period,
        "start_date": today.strftime("%Y-%m-%d"),
        "end_date": end.strftime("%Y-%m-%d"),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    license_path().write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record
