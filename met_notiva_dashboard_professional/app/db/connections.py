from contextlib import contextmanager

import pyodbc
from flask import current_app


@contextmanager
def erp_connection():
    conn = pyodbc.connect(current_app.config["ERP_CONNECTION_STRING"])
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def user_connection():
    conn = pyodbc.connect(current_app.config["USER_CONNECTION_STRING"])
    try:
        yield conn
    finally:
        conn.close()
