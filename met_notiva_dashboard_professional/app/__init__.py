from flask import Flask, flash, redirect, request, session, url_for

from app.config import Settings
from app.auth.routes import auth_bp
from app.dashboard.routes import dashboard_bp
from app.reports.cari.routes import cari_bp
from app.reports.orders.routes import orders_bp
from app.reports.sales.routes import sales_bp
from app.license import license_status


def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    settings = Settings()
    app.config.from_object(settings)
    app.config["SETTINGS_OBJECT"] = settings

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(cari_bp)
    app.register_blueprint(sales_bp)

    @app.before_request
    def enforce_license():
        if "user_id" not in session:
            return None

        allowed_endpoints = {
            "static",
            "auth.logout",
            "dashboard.settings",
            "dashboard.api_settings",
            "dashboard.api_save_settings",
            "dashboard.api_test_sql",
            "dashboard.api_license_status",
            "dashboard.api_save_license",
        }
        if request.endpoint in allowed_endpoints:
            return None

        status = license_status()
        if not status["valid"]:
            flash("Lisans suresi doldu veya lisans bulunamadi. Lutfen lisans yenilemesi yapiniz.", "danger")
            return redirect(url_for("dashboard.settings"))

        return None

    return app
