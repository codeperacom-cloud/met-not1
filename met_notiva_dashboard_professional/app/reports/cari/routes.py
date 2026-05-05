import os
import smtplib
import tempfile
import time
from email.message import EmailMessage

from flask import Blueprint, current_app, render_template, request
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.auth.security import login_required
from app.common.responses import fail, ok
from app.db.connections import erp_connection
from app.db.settings import firm_prefix, get_current_settings, table_prefix
from app.reports.orders.routes import requested_settings


cari_bp = Blueprint("cari", __name__, url_prefix="")


@cari_bp.route("/reports/cari")
@login_required
def report():
    firm_nr, period_nr = requested_settings()
    return render_template("reports/cari.html", firm_nr=firm_nr, period_nr=period_nr)


@cari_bp.route("/api/cariler")
@login_required
def api_cariler():
    try:
        firm_nr, period_nr = requested_settings()
        prefix = table_prefix(firm_nr, period_nr)
        fprefix = firm_prefix(firm_nr)
        query = f"""
            SELECT
                CLC.CODE,
                CLC.DEFINITION_,
                SUM(CASE WHEN CLL.SIGN = 0 THEN CLL.AMOUNT ELSE 0 END),
                SUM(CASE WHEN CLL.SIGN = 1 THEN CLL.AMOUNT ELSE 0 END),
                SUM(CASE WHEN CLL.SIGN = 1 THEN CLL.AMOUNT ELSE 0 END) -
                SUM(CASE WHEN CLL.SIGN = 0 THEN CLL.AMOUNT ELSE 0 END),
                CLC.LOGICALREF
            FROM {prefix}CLFLINE CLL
            LEFT JOIN {fprefix}CLCARD CLC ON CLL.CLIENTREF = CLC.LOGICALREF
            GROUP BY CLC.CODE, CLC.DEFINITION_, CLC.LOGICALREF
            ORDER BY CLC.CODE
        """
        with erp_connection() as conn:
            rows = conn.cursor().execute(query).fetchall()
        data = []
        for row in rows:
            bakiye = float(row[4] or 0)
            data.append(
                {
                    "carikodu": row[0],
                    "unvan": row[1],
                    "borc": float(row[2] or 0),
                    "alacak": float(row[3] or 0),
                    "bakiye": bakiye,
                    "durum": "BORCLU" if bakiye < 0 else "ALACAKLI",
                    "clientref": row[5],
                }
            )
        return ok(data)
    except Exception as exc:
        return fail(str(exc))


@cari_bp.route("/api/ekstre/<int:clientref>")
@login_required
def api_ekstre(clientref: int):
    try:
        firm_nr, period_nr = requested_settings()
        start_date = request.args.get("startDate")
        end_date = request.args.get("endDate")
        prefix = table_prefix(firm_nr, period_nr)

        params = [clientref]
        date_filter = ""
        if start_date and end_date:
            date_filter = "AND CLL.DATE_ BETWEEN ? AND ?"
            params.extend([start_date, end_date])

        query = f"""
            SELECT
                CONVERT(varchar, CLL.DATE_, 105),
                CLL.TRANNO,
                CASE
                    WHEN CLL.TRCODE=31 THEN 'Mal Alim Fat.'
                    WHEN CLL.TRCODE=37 THEN 'Perakende Satis Fat.'
                    WHEN CLL.TRCODE=38 THEN 'Toptan Satis Fat.'
                    WHEN CLL.TRCODE=1 THEN 'Nakit Tahsilat'
                    WHEN CLL.TRCODE=2 THEN 'Nakit Odeme'
                    ELSE 'Diger (' + CAST(CLL.TRCODE AS VARCHAR) + ')'
                END,
                CLL.AMOUNT,
                CASE WHEN CLL.SIGN = 1 THEN 'ALACAK' ELSE 'BORC' END
            FROM {prefix}CLFLINE CLL
            WHERE CLL.CLIENTREF = ?
            {date_filter}
            ORDER BY CLL.DATE_
        """
        with erp_connection() as conn:
            rows = conn.cursor().execute(query, tuple(params)).fetchall()
        return ok([list(row) for row in rows])
    except Exception as exc:
        return fail(str(exc))


@cari_bp.route("/api/send-ekstre-mail/<int:clientref>", methods=["POST"])
@login_required
def api_send_ekstre_mail(clientref: int):
    try:
        payload = request.get_json(silent=True) or {}
        firm_nr, period_nr = get_current_settings()
        start_date = payload.get("startDate")
        end_date = payload.get("endDate")
        carikodu = payload.get("carikodu", "")
        unvan = payload.get("unvan", "Cari")
        prefix = table_prefix(firm_nr, period_nr)
        fprefix = firm_prefix(firm_nr)

        smtp_host = current_app.config["SMTP_HOST"]
        smtp_user = current_app.config["SMTP_USER"]
        smtp_password = current_app.config["SMTP_PASSWORD"]
        smtp_from = current_app.config["SMTP_FROM"] or smtp_user
        if not smtp_host or not smtp_from:
            return fail("SMTP ayarlari eksik. .env icinde SMTP_HOST, SMTP_FROM ve gerekirse SMTP_USER/SMTP_PASSWORD doldurun.", 400)

        with erp_connection() as conn:
            cursor = conn.cursor()
            email_row = cursor.execute(
                f"SELECT EMAILADDR FROM {fprefix}CLCARD WHERE LOGICALREF = ?",
                (clientref,),
            ).fetchone()
            email = email_row[0] if email_row and email_row[0] else None
            if not email:
                return fail("Bu caride e-posta adresi bulunamadi.", 400)

            devreden_bakiye = 0
            if start_date:
                devreden_row = cursor.execute(
                    f"""
                    SELECT
                        SUM(CASE WHEN SIGN = 1 THEN AMOUNT ELSE 0 END) -
                        SUM(CASE WHEN SIGN = 0 THEN AMOUNT ELSE 0 END)
                    FROM {prefix}CLFLINE
                    WHERE CLIENTREF = ? AND DATE_ < ?
                    """,
                    (clientref, start_date),
                ).fetchone()
                devreden_bakiye = float(devreden_row[0] or 0)

            params = [clientref]
            date_filter = ""
            if start_date and end_date:
                date_filter = "AND DATE_ BETWEEN ? AND ?"
                params.extend([start_date, end_date])

            rows = cursor.execute(
                f"""
                SELECT
                    CONVERT(varchar, DATE_, 105),
                    ISNULL(TRANNO, ''),
                    CASE
                        WHEN TRCODE=31 THEN 'Mal Alim Fat.'
                        WHEN TRCODE=32 THEN 'Perakende Satis Iade Fat.'
                        WHEN TRCODE=33 THEN 'Toptan Satis Iade Fat.'
                        WHEN TRCODE=34 THEN 'Alinan Hizmet Fat.'
                        WHEN TRCODE=36 THEN 'Alim Iade Fat.'
                        WHEN TRCODE=37 THEN 'Perakende Satis Fat.'
                        WHEN TRCODE=38 THEN 'Toptan Satis Fat.'
                        WHEN TRCODE=39 THEN 'Verilen Hizmet Fat.'
                        WHEN TRCODE=1 THEN 'Nakit Tahsilat'
                        WHEN TRCODE=2 THEN 'Nakit Odeme'
                        ELSE 'Diger'
                    END,
                    AMOUNT,
                    SIGN
                FROM {prefix}CLFLINE
                WHERE CLIENTREF = ?
                {date_filter}
                ORDER BY DATE_
                """,
                tuple(params),
            ).fetchall()

            bakiye_row = cursor.execute(
                f"""
                SELECT
                    SUM(CASE WHEN SIGN=1 THEN AMOUNT ELSE 0 END) -
                    SUM(CASE WHEN SIGN=0 THEN AMOUNT ELSE 0 END)
                FROM {prefix}CLFLINE
                WHERE CLIENTREF = ?
                """,
                (clientref,),
            ).fetchone()
            bakiye = float(bakiye_row[0] or 0)

        pdf_path = build_ekstre_pdf(rows, devreden_bakiye, bakiye, carikodu, unvan, start_date)
        send_ekstre_email(pdf_path, email, smtp_from, unvan, bakiye)
        os.remove(pdf_path)
        return ok(message=f"Ekstre {email} adresine gonderildi.")
    except Exception as exc:
        return fail(str(exc))


def build_ekstre_pdf(rows, devreden_bakiye, bakiye, carikodu, unvan, start_date):
    pdf_path = os.path.join(tempfile.gettempdir(), f"ekstre_{time.time()}.pdf")
    doc = SimpleDocTemplate(pdf_path, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=42, bottomMargin=36)
    title_style = ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=18, textColor=colors.HexColor("#172033"))
    sub_style = ParagraphStyle("sub", fontName="Helvetica", fontSize=10, textColor=colors.HexColor("#657084"))

    elements = [
        Paragraph("CARI EKSTRE", title_style),
        Paragraph(f"{unvan} ({carikodu})", sub_style),
        Spacer(1, 14),
    ]

    bakiye_text = f"{abs(bakiye):,.2f} TL {'BORC' if bakiye < 0 else 'ALACAK'}"
    elements.append(
        Table(
            [["Rapor Tarihi", time.strftime("%d.%m.%Y")], ["Guncel Bakiye", bakiye_text]],
            colWidths=[140, 300],
            style=[
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f6f7f9")),
                ("BOX", (0, 0), (-1, -1), .5, colors.lightgrey),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ],
        )
    )
    elements.append(Spacer(1, 18))

    table_data = [["Tarih", "Fis No", "Fis Turu", "Borc", "Alacak"]]
    toplam_borc = 0
    toplam_alacak = 0
    if start_date and devreden_bakiye:
        dev_borc = abs(devreden_bakiye) if devreden_bakiye < 0 else 0
        dev_alacak = devreden_bakiye if devreden_bakiye > 0 else 0
        toplam_borc += dev_borc
        toplam_alacak += dev_alacak
        table_data.append([start_date, "", "DEVREDEN BAKIYE", f"{dev_borc:,.2f}" if dev_borc else "", f"{dev_alacak:,.2f}" if dev_alacak else ""])

    for tarih, fis_no, fis_turu, tutar, sign in rows:
        tutar = float(tutar or 0)
        borc = tutar if sign == 0 else 0
        alacak = tutar if sign == 1 else 0
        toplam_borc += borc
        toplam_alacak += alacak
        table_data.append([tarih, fis_no, fis_turu, f"{borc:,.2f}" if borc else "", f"{alacak:,.2f}" if alacak else ""])

    table_data.append(["", "TOPLAM", "", f"{toplam_borc:,.2f}", f"{toplam_alacak:,.2f}"])
    table = Table(table_data, colWidths=[72, 92, 190, 82, 82], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#172033")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#eef4f4")]),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e6eaf0")),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), .25, colors.lightgrey),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(table)
    doc.build(elements)
    return pdf_path


def send_ekstre_email(pdf_path, to_email, from_email, unvan, bakiye):
    msg = EmailMessage()
    msg["Subject"] = f"Cari Ekstre - {unvan}"
    msg["From"] = from_email
    msg["To"] = to_email
    bakiye_text = f"{abs(bakiye):,.2f} TL {'BORC' if bakiye < 0 else 'ALACAK'}"
    msg.set_content(
        f"""Sayin {unvan},

Cari hesap ekstreniz ekte yer almaktadir.

Guncel bakiyeniz: {bakiye_text}

Iyi calismalar."""
    )
    with open(pdf_path, "rb") as pdf_file:
        msg.add_attachment(pdf_file.read(), maintype="application", subtype="pdf", filename="ekstre.pdf")

    smtp_host = current_app.config["SMTP_HOST"]
    smtp_port = current_app.config["SMTP_PORT"]
    smtp_user = current_app.config["SMTP_USER"]
    smtp_password = current_app.config["SMTP_PASSWORD"]

    if current_app.config["SMTP_USE_SSL"]:
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as smtp:
            if smtp_user:
                smtp.login(smtp_user, smtp_password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(smtp_host, smtp_port) as smtp:
            smtp.starttls()
            if smtp_user:
                smtp.login(smtp_user, smtp_password)
            smtp.send_message(msg)
