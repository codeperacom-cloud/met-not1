import re

from flask import current_app

from app.db.connections import user_connection


FIRM_PERIOD_RE = re.compile(r"^\d{1,3}$")


def normalize_firm_nr(value: str | int | None) -> str:
    value = str(value or "").strip()
    if not FIRM_PERIOD_RE.match(value):
        raise ValueError("Gecersiz firma numarasi.")
    return value.zfill(3)


def normalize_period_nr(value: str | int | None) -> str:
    value = str(value or "").strip()
    if not FIRM_PERIOD_RE.match(value):
        raise ValueError("Gecersiz donem numarasi.")
    return value.zfill(2)


def table_prefix(firm_nr: str, period_nr: str) -> str:
    return f"LG_{normalize_firm_nr(firm_nr)}_{normalize_period_nr(period_nr)}_"


def firm_prefix(firm_nr: str) -> str:
    return f"LG_{normalize_firm_nr(firm_nr)}_"


def get_current_settings() -> tuple[str, str]:
    try:
        with user_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT FirmNr, PeriodNr FROM CurrentSettings WHERE Id = 1")
            row = cursor.fetchone()
            if row and row[0] and row[1]:
                return normalize_firm_nr(row[0]), normalize_period_nr(row[1])
    except Exception:
        pass

    return (
        normalize_firm_nr(current_app.config["DEFAULT_FIRM_NR"]),
        normalize_period_nr(current_app.config["DEFAULT_PERIOD_NR"]),
    )


def save_current_settings(firm_nr: str, period_nr: str) -> None:
    firm_nr = normalize_firm_nr(firm_nr)
    period_nr = normalize_period_nr(period_nr)

    with user_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            MERGE CurrentSettings AS target
            USING (VALUES (1, ?, ?)) AS source (Id, FirmNr, PeriodNr)
            ON target.Id = source.Id
            WHEN MATCHED THEN
                UPDATE SET FirmNr = source.FirmNr,
                           PeriodNr = source.PeriodNr,
                           LastUpdated = GETDATE()
            WHEN NOT MATCHED THEN
                INSERT (Id, FirmNr, PeriodNr)
                VALUES (source.Id, source.FirmNr, source.PeriodNr);
            """,
            (firm_nr, period_nr),
        )
        conn.commit()
