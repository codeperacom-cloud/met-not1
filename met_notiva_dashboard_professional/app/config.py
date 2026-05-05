import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


@dataclass
class Settings:
    SECRET_KEY: str = env("SECRET_KEY", "dev-only-change-me")
    DEBUG: bool = env("FLASK_ENV", "production").lower() == "development"

    SQL_DRIVER: str = env("SQL_DRIVER", "SQL Server")
    SQL_SERVER: str = env("SQL_SERVER")
    SQL_USER: str = env("SQL_USER")
    SQL_PASSWORD: str = env("SQL_PASSWORD")
    SQL_ENCRYPT: str = env("SQL_ENCRYPT", "no")
    SQL_TRUST_SERVER_CERTIFICATE: str = env("SQL_TRUST_SERVER_CERTIFICATE", "yes")

    ERP_DATABASE: str = env("ERP_DATABASE", "METENTERPRISE")
    USER_DATABASE: str = env("USER_DATABASE", "NotivaDB")

    DEFAULT_FIRM_NR: str = env("DEFAULT_FIRM_NR", "007")
    DEFAULT_PERIOD_NR: str = env("DEFAULT_PERIOD_NR", "01")

    SMTP_HOST: str = env("SMTP_HOST")
    SMTP_PORT: int = int(env("SMTP_PORT", "587") or 587)
    SMTP_USER: str = env("SMTP_USER")
    SMTP_PASSWORD: str = env("SMTP_PASSWORD")
    SMTP_FROM: str = env("SMTP_FROM")
    SMTP_USE_SSL: bool = env("SMTP_USE_SSL", "false").lower() in {"1", "true", "yes"}

    def __post_init__(self):
        self.ERP_CONNECTION_STRING = self.connection_string(self.ERP_DATABASE)
        self.USER_CONNECTION_STRING = self.connection_string(self.USER_DATABASE)

    def connection_string(self, database: str) -> str:
        return (
            f"DRIVER={{{self.SQL_DRIVER}}};"
            f"SERVER={self.SQL_SERVER};"
            f"DATABASE={database};"
            f"UID={self.SQL_USER};"
            f"PWD={self.SQL_PASSWORD};"
            f"TrustServerCertificate={self.SQL_TRUST_SERVER_CERTIFICATE};"
            f"Encrypt={self.SQL_ENCRYPT};"
        )
