from calendar import monthrange
from datetime import date, datetime

from flask import Blueprint, jsonify, render_template, request

from app.auth.security import login_required
from app.common.responses import fail, ok
from app.db.connections import erp_connection
from app.db.settings import firm_prefix, get_current_settings, table_prefix


sales_bp = Blueprint("sales", __name__, url_prefix="")


def date_sql(value) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return f"{value:%Y-%m-%d} 00:00:00"
    return str(value)


def period_bounds(cursor, firm_nr: str, period_nr: str) -> tuple[str, str]:
    row = cursor.execute(
        """
        SELECT BEGDATE, ENDDATE
        FROM L_CAPIPERIOD
        WHERE FIRMNR = ? AND NR = ?
        """,
        (int(firm_nr), int(period_nr)),
    ).fetchone()
    if not row or not row[0] or not row[1]:
        year = date.today().year
        return f"{year}-01-01 00:00:00", f"{year}-12-31 23:59:59"
    start = date_sql(row[0])
    end_value = row[1]
    if isinstance(end_value, datetime):
        end = end_value.strftime("%Y-%m-%d 23:59:59")
    elif isinstance(end_value, date):
        end = f"{end_value:%Y-%m-%d} 23:59:59"
    else:
        end = str(end_value)
    return start, end


def date_range_for_month(selected_month: str, period_start: str, period_end: str) -> tuple[str, str, str]:
    if not selected_month:
        return period_start, period_end, "Donem"

    period_year = int(period_start[:4])
    month = int(selected_month)
    last_day = monthrange(period_year, month)[1]
    month_start = f"{period_year}-{month:02d}-01 00:00:00"
    month_end = f"{period_year}-{month:02d}-{last_day:02d} 23:59:59"
    return max(month_start, period_start), min(month_end, period_end), f"{period_year}-{month:02d}"


def salesman_filter(salesman: str, table_alias: str = "S") -> tuple[str, list[str]]:
    if not salesman:
        return "", []
    if salesman == "Belirtilmemis":
        return f" AND (SLS.DEFINITION_ IS NULL OR {table_alias}.SALESMANREF = 0)", []
    return " AND SLS.DEFINITION_ = ?", [salesman]


@sales_bp.route("/reports/sales-performance")
@login_required
def report():
    return render_template("reports/sales_performance.html")


@sales_bp.route("/api/sales-performance/summary")
@login_required
def api_summary():
    try:
        firm_nr, period_nr = get_current_settings()
        prefix = table_prefix(firm_nr, period_nr)
        query = f"""
            SELECT
                ISNULL(SLS.DEFINITION_, 'Belirtilmemis'),
                SUM(CASE WHEN S.TRCODE = 8 THEN S.AMOUNT ELSE -S.AMOUNT END),
                SUM(CASE WHEN S.TRCODE = 8 THEN S.LINENET ELSE -S.LINENET END)
            FROM {prefix}STLINE S
            LEFT JOIN LG_SLSMAN SLS ON SLS.LOGICALREF = S.SALESMANREF
            WHERE S.CANCELLED = 0 AND S.TRCODE IN (8, 3)
            GROUP BY SLS.DEFINITION_
            ORDER BY 3 DESC
        """
        with erp_connection() as conn:
            rows = conn.cursor().execute(query).fetchall()
        return ok(
            [
                {"satis_eleman": r[0], "miktar": float(r[1] or 0), "net_tutar": float(r[2] or 0)}
                for r in rows
            ]
        )
    except Exception as exc:
        return fail(str(exc))


@sales_bp.route("/api/sales-performance/detail")
@login_required
def api_detail():
    try:
        firm_nr, period_nr = get_current_settings()
        prefix = table_prefix(firm_nr, period_nr)
        fprefix = firm_prefix(firm_nr)
        params = []
        filters = ""

        start_date = request.args.get("startDate")
        end_date = request.args.get("endDate")
        salesman = request.args.get("salesman")
        cari = request.args.get("cari")

        if start_date and end_date:
            filters += " AND S.DATE_ BETWEEN ? AND ?"
            params.extend([start_date, end_date])
        if salesman:
            filters += " AND ISNULL(SLS.DEFINITION_, 'Belirtilmemis') = ?"
            params.append(salesman)
        if cari:
            filters += " AND CLC.DEFINITION_ = ?"
            params.append(cari)

        query = f"""
            SELECT
                ISNULL(SLS.DEFINITION_, 'Belirtilmemis'),
                ISNULL(CLC.DEFINITION_, 'Belirtilmemis'),
                ISNULL(I.CODE, ''),
                ISNULL(I.NAME, ''),
                SUM(CASE WHEN S.TRCODE = 8 THEN S.AMOUNT ELSE -S.AMOUNT END),
                SUM(CASE WHEN S.TRCODE = 8 THEN S.LINENET ELSE -S.LINENET END)
            FROM {prefix}STLINE S
            LEFT JOIN LG_SLSMAN SLS ON SLS.LOGICALREF = S.SALESMANREF
            LEFT JOIN {fprefix}CLCARD CLC ON CLC.LOGICALREF = S.CLIENTREF
            LEFT JOIN {fprefix}ITEMS I ON I.LOGICALREF = S.STOCKREF
            WHERE S.CANCELLED = 0 AND S.TRCODE IN (8, 3)
            {filters}
            GROUP BY SLS.DEFINITION_, CLC.DEFINITION_, I.CODE, I.NAME
            ORDER BY 6 DESC
        """
        with erp_connection() as conn:
            rows = conn.cursor().execute(query, tuple(params)).fetchall()
        return ok(
            [
                {
                    "satis_eleman": r[0],
                    "cari_unvan": r[1],
                    "urun_kodu": r[2],
                    "urun_adi": r[3],
                    "miktar": float(r[4] or 0),
                    "net_tutar": float(r[5] or 0),
                }
                for r in rows
            ]
        )
    except Exception as exc:
        return fail(str(exc))


@sales_bp.route("/api/sales-performance/salesmen")
@login_required
def api_salesmen():
    try:
        firm_nr, period_nr = get_current_settings()
        prefix = table_prefix(firm_nr, period_nr)
        with erp_connection() as conn:
            rows = conn.cursor().execute(
                f"""
                SELECT DISTINCT ISNULL(SLS.DEFINITION_, 'Belirtilmemis')
                FROM {prefix}STLINE S
                LEFT JOIN LG_SLSMAN SLS ON SLS.LOGICALREF = S.SALESMANREF
                WHERE S.CANCELLED = 0 AND S.TRCODE IN (8, 3)
                ORDER BY 1
                """
            ).fetchall()
        return jsonify({"success": True, "salesmen": [r[0] for r in rows]})
    except Exception:
        return jsonify({"success": False, "salesmen": []})


@sales_bp.route("/api/sales-performance/cariler")
@login_required
def api_cariler():
    try:
        firm_nr, _ = get_current_settings()
        fprefix = firm_prefix(firm_nr)
        with erp_connection() as conn:
            rows = conn.cursor().execute(
                f"SELECT DISTINCT DEFINITION_ FROM {fprefix}CLCARD WHERE DEFINITION_ IS NOT NULL ORDER BY DEFINITION_"
            ).fetchall()
        return jsonify({"success": True, "cariler": [r[0] for r in rows if r[0]]})
    except Exception:
        return jsonify({"success": False, "cariler": []})


@sales_bp.route("/api/sales-performance/monthly")
@login_required
def api_monthly():
    try:
        firm_nr, period_nr = get_current_settings()
        prefix = table_prefix(firm_nr, period_nr)
        query = f"""
            SELECT
                FORMAT(S.DATE_, 'yyyy-MM'),
                ISNULL(SLS.DEFINITION_, 'Belirtilmemis'),
                SUM(CASE WHEN S.TRCODE = 8 THEN S.AMOUNT ELSE -S.AMOUNT END),
                SUM(CASE WHEN S.TRCODE = 8 THEN S.LINENET ELSE -S.LINENET END)
            FROM {prefix}STLINE S
            LEFT JOIN LG_SLSMAN SLS ON SLS.LOGICALREF = S.SALESMANREF
            WHERE S.CANCELLED = 0 AND S.TRCODE IN (8, 3)
            GROUP BY FORMAT(S.DATE_, 'yyyy-MM'), SLS.DEFINITION_
            ORDER BY 1
        """
        with erp_connection() as conn:
            rows = conn.cursor().execute(query).fetchall()
        return ok(
            [
                {"ay": r[0], "satis_eleman": r[1], "miktar": float(r[2] or 0), "net_tutar": float(r[3] or 0)}
                for r in rows
            ]
        )
    except Exception as exc:
        return fail(str(exc))


@sales_bp.route("/api/sales-performance/modal-summary")
@login_required
def api_modal_summary():
    try:
        firm_nr, period_nr = get_current_settings()
        st_prefix = table_prefix(firm_nr, period_nr)
        fprefix = firm_prefix(firm_nr)
        salesman = request.args.get("salesman", "")
        selected_month = request.args.get("month", "")

        st_where, st_params = salesman_filter(salesman, "S")
        order_where, order_params = salesman_filter(salesman, "O")

        with erp_connection() as conn:
            cursor = conn.cursor()
            year_start, year_end = period_bounds(cursor, firm_nr, period_nr)
            month_start, month_end, active_range_label = date_range_for_month(selected_month, year_start, year_end)
            year_sales = cursor.execute(
                f"""
                SELECT
                    ISNULL(SUM(CASE WHEN S.TRCODE = 8 THEN S.LINENET ELSE -S.LINENET END), 0),
                    ISNULL(SUM(CASE WHEN S.TRCODE = 8 THEN S.AMOUNT ELSE -S.AMOUNT END), 0)
                FROM {st_prefix}STLINE S
                LEFT JOIN LG_SLSMAN SLS ON SLS.LOGICALREF = S.SALESMANREF
                WHERE S.CANCELLED = 0 AND S.TRCODE IN (8, 3)
                  AND S.DATE_ BETWEEN ? AND ?
                  {st_where}
                """,
                tuple([year_start, year_end] + st_params),
            ).fetchone()

            year_orders = cursor.execute(
                f"""
                SELECT COUNT(*), ISNULL(SUM(O.GROSSTOTAL), 0)
                FROM {st_prefix}ORFICHE O
                LEFT JOIN LG_SLSMAN SLS ON SLS.LOGICALREF = O.SALESMANREF
                WHERE O.CANCELLED = 0 AND O.TRCODE = 1
                  AND O.DATE_ BETWEEN ? AND ?
                  {order_where}
                """,
                tuple([year_start, year_end] + order_params),
            ).fetchone()

            month_sales = cursor.execute(
                f"""
                SELECT
                    ISNULL(SUM(CASE WHEN S.TRCODE = 8 THEN S.LINENET ELSE -S.LINENET END), 0),
                    ISNULL(SUM(CASE WHEN S.TRCODE = 8 THEN S.AMOUNT ELSE -S.AMOUNT END), 0)
                FROM {st_prefix}STLINE S
                LEFT JOIN LG_SLSMAN SLS ON SLS.LOGICALREF = S.SALESMANREF
                WHERE S.CANCELLED = 0 AND S.TRCODE IN (8, 3)
                  AND S.DATE_ BETWEEN ? AND ?
                  {st_where}
                """,
                tuple([month_start, month_end] + st_params),
            ).fetchone()

            month_orders = cursor.execute(
                f"""
                SELECT COUNT(*)
                FROM {st_prefix}ORFICHE O
                LEFT JOIN LG_SLSMAN SLS ON SLS.LOGICALREF = O.SALESMANREF
                WHERE O.CANCELLED = 0 AND O.TRCODE = 1
                  AND O.DATE_ BETWEEN ? AND ?
                  {order_where}
                """,
                tuple([month_start, month_end] + order_params),
            ).fetchone()

            cari_rows = cursor.execute(
                f"""
                SELECT
                    ISNULL(CLC.DEFINITION_, 'Belirtilmemis'),
                    SUM(CASE WHEN S.TRCODE = 8 THEN S.LINENET ELSE -S.LINENET END)
                FROM {st_prefix}STLINE S
                LEFT JOIN LG_SLSMAN SLS ON SLS.LOGICALREF = S.SALESMANREF
                LEFT JOIN {fprefix}CLCARD CLC ON CLC.LOGICALREF = S.CLIENTREF
                WHERE S.CANCELLED = 0 AND S.TRCODE IN (8, 3)
                  AND S.DATE_ BETWEEN ? AND ?
                  {st_where}
                GROUP BY CLC.DEFINITION_
                ORDER BY 2 DESC
                """,
                tuple([month_start, month_end] + st_params),
            ).fetchall()

            urun_rows = cursor.execute(
                f"""
                SELECT
                    ISNULL(I.CODE, ''),
                    ISNULL(I.NAME, ''),
                    SUM(CASE WHEN S.TRCODE = 8 THEN S.AMOUNT ELSE -S.AMOUNT END)
                FROM {st_prefix}STLINE S
                LEFT JOIN LG_SLSMAN SLS ON SLS.LOGICALREF = S.SALESMANREF
                LEFT JOIN {fprefix}ITEMS I ON I.LOGICALREF = S.STOCKREF
                WHERE S.CANCELLED = 0 AND S.TRCODE IN (8, 3)
                  AND S.DATE_ BETWEEN ? AND ?
                  {st_where}
                GROUP BY I.CODE, I.NAME
                HAVING SUM(CASE WHEN S.TRCODE = 8 THEN S.AMOUNT ELSE -S.AMOUNT END) > 0
                ORDER BY 3 DESC
                """,
                tuple([month_start, month_end] + st_params),
            ).fetchall()

        year_order_count = int(year_orders[0] or 0)
        year_order_total = float(year_orders[1] or 0)
        data = {
            "year_total_amount": float(year_sales[0] or 0),
            "year_total_qty": float(year_sales[1] or 0),
            "year_order_count": year_order_count,
            "year_avg_order": year_order_total / year_order_count if year_order_count else 0,
            "month_total_amount": float(month_sales[0] or 0),
            "month_total_qty": float(month_sales[1] or 0),
            "month_order_count": int(month_orders[0] or 0),
            "active_range_label": active_range_label,
            "period_start": year_start[:10],
            "period_end": year_end[:10],
            "cari_data": [{"cari_unvan": r[0], "tutar": float(r[1] or 0)} for r in cari_rows],
            "urun_data": [{"urun_kodu": r[0], "urun_adi": r[1], "miktar": float(r[2] or 0)} for r in urun_rows],
        }
        return ok(data)
    except Exception as exc:
        return fail(str(exc))
