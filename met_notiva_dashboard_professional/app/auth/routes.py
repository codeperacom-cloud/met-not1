from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from app.db.connections import user_connection
from app.license import license_status


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        try:
            user = find_active_user(username)
            if user and password_matches(user.password, password):
                session.clear()
                session["user_id"] = user.id
                session["username"] = user.username
                session["full_name"] = user.full_name or user.username
                flash("Hos geldiniz.", "success")
                if not license_status()["valid"]:
                    flash("Lisans yenilemesi yapiniz.", "danger")
                    return redirect(url_for("dashboard.settings"))
                return redirect(url_for("dashboard.index"))

            flash("Kullanici adi veya sifre hatali.", "danger")
        except Exception:
            flash("Veritabani baglantisi kurulamadi. .env ve SQL Server ayarlarini kontrol edin.", "danger")

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Basariyla cikis yapildi.", "info")
    return redirect(url_for("auth.login"))


class UserRecord:
    def __init__(self, row):
        self.id = row[0]
        self.username = row[1]
        self.full_name = row[2]
        self.password = row[3]


def find_active_user(username: str) -> UserRecord | None:
    if not username:
        return None

    with user_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT Id, Username, FullName, Password
            FROM Users
            WHERE Username = ? AND IsActive = 1
            """,
            (username,),
        )
        row = cursor.fetchone()
        return UserRecord(row) if row else None


def password_matches(stored_password: str, plain_password: str) -> bool:
    if not stored_password:
        return False

    if stored_password.startswith(("pbkdf2:", "scrypt:")):
        return check_password_hash(stored_password, plain_password)

    # Legacy compatibility: lets the app keep working until existing passwords
    # are migrated to hashes.
    return stored_password == plain_password
