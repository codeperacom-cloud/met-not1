import os
from datetime import date
from pathlib import Path

import pyodbc
from flask import Blueprint, current_app, jsonify, render_template, request, session
from app.common.responses import fail, ok
from app.db.connections import erp_connection
from app.db.settings import firm_prefix, get_current_settings, table_prefix
from app.license import license_status, save_license

from app.auth.security import login_required


dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
def index():
    return render_template(
        "dashboard.html",
        username=session.get("username"),
        full_name=session.get("full_name"),
    )


@dashboard_bp.route("/api/dashboard-summary")
@login_required
def api_dashboard_summary():
    try:
        firm_nr, period_nr = get_current_settings()
        prefix = table_prefix(firm_nr, period_nr)
        fprefix = firm_prefix(firm_nr)
        today = date.today().strftime("%Y-%m-%d")

        with erp_connection() as conn:
            cursor = conn.cursor()
            balance_rows = cursor.execute(
                f"""
                SELECT
                    ISNULL(CLC.CODE, ''),
                    ISNULL(CLC.DEFINITION_, 'Belirtilmemis'),
                    SUM(CASE WHEN CLL.SIGN = 1 THEN CLL.AMOUNT ELSE 0 END) -
                    SUM(CASE WHEN CLL.SIGN = 0 THEN CLL.AMOUNT ELSE 0 END) AS Bakiye
                FROM {prefix}CLFLINE CLL
                LEFT JOIN {fprefix}CLCARD CLC ON CLC.LOGICALREF = CLL.CLIENTREF
                GROUP BY CLC.CODE, CLC.DEFINITION_
                HAVING ABS(SUM(CASE WHEN CLL.SIGN = 1 THEN CLL.AMOUNT ELSE 0 END) -
                           SUM(CASE WHEN CLL.SIGN = 0 THEN CLL.AMOUNT ELSE 0 END)) > 0
                ORDER BY Bakiye DESC
                """
            ).fetchall()

            order_rows = cursor.execute(
                f"""
                SELECT TOP 6
                    ORF.FICHENO,
                    CONVERT(varchar, ORF.DATE_, 105),
                    ISNULL(CLC.DEFINITION_, 'Belirtilmemis'),
                    ORF.NETTOTAL
                FROM {prefix}ORFICHE ORF
                LEFT JOIN {fprefix}CLCARD CLC ON CLC.LOGICALREF = ORF.CLIENTREF
                WHERE ORF.CANCELLED = 0 AND ORF.TRCODE = 1
                ORDER BY ORF.DATE_ DESC
                """
            ).fetchall()

            sales_rows = cursor.execute(
                f"""
                SELECT TOP 6
                    ISNULL(SLS.DEFINITION_, 'Belirtilmemis'),
                    SUM(CASE WHEN S.TRCODE = 8 THEN S.LINENET ELSE -S.LINENET END)
                FROM {prefix}STLINE S
                LEFT JOIN LG_SLSMAN SLS ON SLS.LOGICALREF = S.SALESMANREF
                WHERE S.CANCELLED = 0 AND S.TRCODE IN (8, 3)
                GROUP BY SLS.DEFINITION_
                ORDER BY 2 DESC
                """
            ).fetchall()

        receivable_rows = [r for r in balance_rows if float(r[2] or 0) > 0]
        debt_rows = [r for r in balance_rows if float(r[2] or 0) < 0]
        total_receivable = sum(float(r[2] or 0) for r in receivable_rows)
        total_debt = abs(sum(float(r[2] or 0) for r in debt_rows))
        high_risk = [r for r in receivable_rows if float(r[2] or 0) >= 100000]
        top_receivables = receivable_rows[:7]
        low_bucket = sum(1 for r in receivable_rows if 0 < float(r[2] or 0) < 50000)
        mid_bucket = sum(1 for r in receivable_rows if 50000 <= float(r[2] or 0) < 250000)
        high_bucket = sum(1 for r in receivable_rows if float(r[2] or 0) >= 250000)

        return ok(
            {
                "firm": firm_nr,
                "period": period_nr,
                "today": today,
                "metrics": {
                    "total_receivable": total_receivable,
                    "total_debt": total_debt,
                    "due_today": 0,
                    "high_risk_count": len(high_risk),
                    "customer_count": len(balance_rows),
                },
                "priority": {
                    "collection_priority": len(receivable_rows),
                    "open_accounts": len(balance_rows),
                    "critical_accounts": len(high_risk),
                },
                "risk": {
                    "low": low_bucket,
                    "medium": mid_bucket,
                    "high": high_bucket,
                },
                "top_receivables": [
                    {"code": r[0], "name": r[1], "amount": float(r[2] or 0)}
                    for r in top_receivables
                ],
                "recent_orders": [
                    {"fiche": r[0], "date": r[1], "customer": r[2], "amount": float(r[3] or 0)}
                    for r in order_rows
                ],
                "salesmen": [
                    {"name": r[0], "amount": float(r[1] or 0)}
                    for r in sales_rows
                ],
                "actions": [
                    {"title": "Cari bakiye kontrolu", "text": "En yuksek bakiyeli cariler incelendi."},
                    {"title": "Siparis analizi", "text": "Son siparis hareketleri guncellendi."},
                    {"title": "Satis performansi", "text": "Personel bazli satis ozeti hazirlandi."},
                ],
            }
        )
    except Exception as exc:
        return fail(str(exc))


@dashboard_bp.route("/reports/collections")
@login_required
def collections():
    return render_template("placeholder.html", title="Tahsilat listesi", description="Tahsilat takip ekrani bu modulde hazirlanacak.")


@dashboard_bp.route("/users")
@login_required
def users():
    return render_template("placeholder.html", title="Kullanicilar", description="Kullanici ve yetki yonetimi bu ekrandan yapilacak.")


@dashboard_bp.route("/settings")
@login_required
def settings():
    return render_template("settings.html")


@dashboard_bp.route("/backup")
@login_required
def backup():
    return render_template("placeholder.html", title="Yedekleme", description="Veritabani ve rapor yedekleme islemleri bu alanda yonetilecek.")


ENV_KEYS = [
    "SQL_SERVER",
    "SQL_DRIVER",
    "SQL_USER",
    "SQL_PASSWORD",
    "SQL_ENCRYPT",
    "SQL_TRUST_SERVER_CERTIFICATE",
    "ERP_DATABASE",
    "USER_DATABASE",
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USER",
    "SMTP_PASSWORD",
    "SMTP_FROM",
    "SMTP_USE_SSL",
]


def env_path() -> Path:
    return Path(current_app.root_path).parent / ".env"


def read_env_file() -> dict:
    values = {}
    path = env_path()
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.strip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def write_env_values(updates: dict) -> None:
    values = read_env_file()
    values.update({key: str(value or "").strip() for key, value in updates.items() if key in ENV_KEYS})
    existing_order = list(values.keys())
    ordered = ["FLASK_ENV", "SECRET_KEY"] + ENV_KEYS + [k for k in existing_order if k not in {"FLASK_ENV", "SECRET_KEY", *ENV_KEYS}]
    lines = []
    for key in ordered:
        if key in values:
            lines.append(f"{key}={values[key]}")
    env_path().write_text("\n".join(lines) + "\n", encoding="utf-8")


def apply_runtime_config(values: dict) -> None:
    for key, value in values.items():
        os.environ[key] = str(value or "")
        if key == "SMTP_PORT":
            current_app.config[key] = int(value or 587)
        elif key == "SMTP_USE_SSL":
            current_app.config[key] = str(value).lower() in {"1", "true", "yes"}
        else:
            current_app.config[key] = value
    current_app.config["ERP_CONNECTION_STRING"] = build_connection_string(current_app.config["ERP_DATABASE"])
    current_app.config["USER_CONNECTION_STRING"] = build_connection_string(current_app.config["USER_DATABASE"])


def build_connection_string(database: str) -> str:
    return (
        f"DRIVER={{{current_app.config['SQL_DRIVER']}}};"
        f"SERVER={current_app.config['SQL_SERVER']};"
        f"DATABASE={database};"
        f"UID={current_app.config['SQL_USER']};"
        f"PWD={current_app.config['SQL_PASSWORD']};"
        f"TrustServerCertificate={current_app.config['SQL_TRUST_SERVER_CERTIFICATE']};"
        f"Encrypt={current_app.config['SQL_ENCRYPT']};"
    )


@dashboard_bp.route("/api/settings")
@login_required
def api_settings():
    values = read_env_file()
    config = {key: values.get(key, str(current_app.config.get(key, ""))) for key in ENV_KEYS}
    return ok({"settings": config, "license": license_status()})


@dashboard_bp.route("/api/settings", methods=["POST"])
@login_required
def api_save_settings():
    try:
        payload = request.get_json(silent=True) or {}
        updates = {key: payload.get(key, "") for key in ENV_KEYS if key in payload}
        write_env_values(updates)
        apply_runtime_config(updates)
        return ok(message="Ayarlar kaydedildi.")
    except Exception as exc:
        return fail(str(exc), 400)


@dashboard_bp.route("/api/settings/test-sql", methods=["POST"])
@login_required
def api_test_sql():
    try:
        payload = request.get_json(silent=True) or {}
        database = payload.get("ERP_DATABASE") or current_app.config["ERP_DATABASE"]
        conn_str = (
            f"DRIVER={{{payload.get('SQL_DRIVER') or current_app.config['SQL_DRIVER']}}};"
            f"SERVER={payload.get('SQL_SERVER') or current_app.config['SQL_SERVER']};"
            f"DATABASE={database};"
            f"UID={payload.get('SQL_USER') or current_app.config['SQL_USER']};"
            f"PWD={payload.get('SQL_PASSWORD') or current_app.config['SQL_PASSWORD']};"
            f"TrustServerCertificate={payload.get('SQL_TRUST_SERVER_CERTIFICATE') or current_app.config['SQL_TRUST_SERVER_CERTIFICATE']};"
            f"Encrypt={payload.get('SQL_ENCRYPT') or current_app.config['SQL_ENCRYPT']};"
        )
        with pyodbc.connect(conn_str, timeout=5) as conn:
            row = conn.cursor().execute("SELECT COUNT(*) FROM L_CAPIFIRM").fetchone()
        return ok({"firm_count": int(row[0] or 0)}, message="SQL baglantisi basarili.")
    except Exception as exc:
        return fail(str(exc), 400)


@dashboard_bp.route("/api/license")
@login_required
def api_license_status():
    return ok(license_status())


@dashboard_bp.route("/api/license", methods=["POST"])
@login_required
def api_save_license():
    try:
        payload = request.get_json(silent=True) or {}
        record = save_license(payload.get("key", ""), payload.get("period", "monthly"))
        return ok({"license": record}, message="Lisans kaydedildi.")
    except Exception as exc:
        return fail(str(exc), 400)
