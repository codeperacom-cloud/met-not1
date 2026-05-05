from flask import Blueprint, render_template, request

from app.auth.security import login_required
from app.common.responses import fail, ok
from app.db.connections import erp_connection
from app.db.settings import (
    firm_prefix,
    get_current_settings,
    normalize_firm_nr,
    normalize_period_nr,
    save_current_settings,
    table_prefix,
)


orders_bp = Blueprint("orders", __name__, url_prefix="")


def requested_settings() -> tuple[str, str]:
    firm_nr = request.args.get("firm")
    period_nr = request.args.get("period")
    if not firm_nr or not period_nr:
        return get_current_settings()
    return normalize_firm_nr(firm_nr), normalize_period_nr(period_nr)


@orders_bp.route("/reports/orders")
@login_required
def report():
    firm_nr, period_nr = requested_settings()
    return render_template("reports/orders.html", firm_nr=firm_nr, period_nr=period_nr)


@orders_bp.route("/api/orders")
@login_required
def api_orders():
    try:
        firm_nr, period_nr = requested_settings()
        prefix = table_prefix(firm_nr, period_nr)
        fprefix = firm_prefix(firm_nr)

        query = f"""
            SELECT
                CASE WHEN ORF.TRCODE = 1 THEN 'Satis' WHEN ORF.TRCODE = 2 THEN 'Satinalma' ELSE 'Diger' END,
                CONVERT(varchar, ORF.DATE_, 105),
                ORF.FICHENO,
                CARI.DEFINITION_,
                ORF.GROSSTOTAL,
                ORF.TOTALVAT,
                ORF.NETTOTAL,
                SUM(ORL.AMOUNT),
                SUM(ORL.SHIPPEDAMOUNT),
                SUM(ORL.AMOUNT) - SUM(ORL.SHIPPEDAMOUNT),
                COALESCE(SLS.DEFINITION_, 'Belirtilmemis'),
                CASE
                    WHEN ORL.STATUS = 4 AND SUM(ORL.AMOUNT) - SUM(ORL.SHIPPEDAMOUNT) = 0 THEN 'Tamami Sevk Edildi'
                    WHEN ORL.STATUS = 4 AND SUM(ORL.AMOUNT) - SUM(ORL.SHIPPEDAMOUNT) > 0 THEN 'Kismen Sevk Edildi'
                    WHEN ORL.STATUS = 1 THEN 'Oneri'
                    WHEN ORL.STATUS = 2 THEN 'Sevk Edilemez'
                    ELSE 'Diger'
                END
            FROM {prefix}ORFICHE ORF
            LEFT JOIN {prefix}ORFLINE ORL ON ORL.ORDFICHEREF = ORF.LOGICALREF
            LEFT JOIN {fprefix}CLCARD CARI ON CARI.LOGICALREF = ORF.CLIENTREF
            LEFT JOIN LG_SLSMAN SLS ON SLS.LOGICALREF = ORF.SALESMANREF
            WHERE ORF.TRCODE = 1
            GROUP BY ORF.DATE_, ORF.FICHENO, CARI.DEFINITION_, ORF.GROSSTOTAL,
                     ORF.TOTALVAT, ORF.NETTOTAL, ORF.TRCODE, ORL.STATUS, SLS.DEFINITION_
            ORDER BY ORF.DATE_ DESC
        """

        with erp_connection() as conn:
            rows = conn.cursor().execute(query).fetchall()

        data = [
            {
                "islem_turu": row[0],
                "tarih": row[1],
                "fis_no": row[2],
                "cari_unvan": row[3],
                "toplam": float(row[4] or 0),
                "kdv": float(row[5] or 0),
                "net_tutar": float(row[6] or 0),
                "siparis_miktar": float(row[7] or 0),
                "sevk_edilen": float(row[8] or 0),
                "bekleyen": float(row[9] or 0),
                "satis_eleman": row[10],
                "siparis_durumu": row[11],
            }
            for row in rows
        ]
        return ok(data)
    except Exception as exc:
        return fail(str(exc))


@orders_bp.route("/api/order-lines/<fis_no>")
@login_required
def api_order_lines(fis_no):
    try:
        firm_nr, period_nr = requested_settings()
        prefix = table_prefix(firm_nr, period_nr)
        fprefix = firm_prefix(firm_nr)

        query = f"""
            SELECT
                CASE WHEN ORF.TRCODE = 1 THEN 'Satis' WHEN ORF.TRCODE = 2 THEN 'Satinalma' ELSE 'Diger' END,
                ORF.FICHENO,
                CONVERT(varchar, ORF.DATE_, 105),
                CARI.DEFINITION_,
                ITM.CODE,
                ITM.NAME,
                ORL.AMOUNT,
                ORL.SHIPPEDAMOUNT,
                ORL.AMOUNT - ORL.SHIPPEDAMOUNT,
                ORL.PRICE,
                ORL.VAT,
                ORL.VATAMNT,
                ORL.LINENET,
                ORL.LINENET + ORL.VATAMNT,
                COALESCE(SLS.DEFINITION_, 'Belirtilmemis')
            FROM {prefix}ORFLINE ORL
            INNER JOIN {prefix}ORFICHE ORF ON ORF.LOGICALREF = ORL.ORDFICHEREF
            LEFT JOIN {fprefix}ITEMS ITM ON ITM.LOGICALREF = ORL.STOCKREF
            LEFT JOIN {fprefix}CLCARD CARI ON CARI.LOGICALREF = ORL.CLIENTREF
            LEFT JOIN LG_SLSMAN SLS ON SLS.LOGICALREF = ORL.SALESMANREF
            WHERE ORF.FICHENO = ? AND ORL.TRCODE = 1
        """
        with erp_connection() as conn:
            rows = conn.cursor().execute(query, (fis_no.strip(),)).fetchall()
        return ok([list(row) for row in rows])
    except Exception as exc:
        return fail(str(exc))


@orders_bp.route("/api/firms")
@login_required
def api_firms():
    try:
        with erp_connection() as conn:
            rows = conn.cursor().execute(
                "SELECT NR, NAME, TITLE FROM L_CAPIFIRM WHERE NR IS NOT NULL ORDER BY NR"
            ).fetchall()
        return ok(firms=[{"nr": str(r[0]).zfill(3), "name": r[1], "title": r[2]} for r in rows])
    except Exception as exc:
        return fail(str(exc))


@orders_bp.route("/api/periods/<firm_nr>")
@login_required
def api_periods(firm_nr):
    try:
        firm_nr = normalize_firm_nr(firm_nr)
        with erp_connection() as conn:
            rows = conn.cursor().execute(
                """
                SELECT NR, BEGDATE, ENDDATE, ACTIVE
                FROM L_CAPIPERIOD
                WHERE FIRMNR = ?
                ORDER BY NR
                """,
                (int(firm_nr),),
            ).fetchall()
        return ok(
            periods=[
                {"nr": str(r[0]).zfill(2), "begdate": str(r[1])[:10], "enddate": str(r[2])[:10], "active": bool(r[3])}
                for r in rows
            ]
        )
    except Exception as exc:
        return fail(str(exc))


@orders_bp.route("/api/set-current-settings", methods=["POST"])
@login_required
def api_set_current_settings():
    try:
        payload = request.get_json(silent=True) or {}
        save_current_settings(payload.get("firm"), payload.get("period"))
        return ok(message="Ayarlar kaydedildi.")
    except Exception as exc:
        return fail(str(exc), 400)


@orders_bp.route("/api/current-firm")
@login_required
def api_current_firm():
    try:
        firm_nr, period_nr = get_current_settings()
        with erp_connection() as conn:
            row = conn.cursor().execute(
                "SELECT TITLE, NAME FROM L_CAPIFIRM WHERE NR = ?",
                (int(firm_nr),),
            ).fetchone()
        label = row[0] or row[1] if row else firm_nr
        return ok({"firm": firm_nr, "period": period_nr, "label": label})
    except Exception as exc:
        return fail(str(exc))
