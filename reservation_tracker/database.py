import sqlite3
from datetime import date

DB_PATH = "reservations.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reservations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                service_type TEXT NOT NULL,
                notes TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)


def get_by_date(date_str):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM reservations WHERE date = ? ORDER BY time ASC",
            (date_str,)
        ).fetchall()


def get_by_month(year, month):
    prefix = f"{year:04d}-{month:02d}"
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM reservations WHERE date LIKE ? ORDER BY date ASC, time ASC",
            (f"{prefix}-%",)
        ).fetchall()


def get_by_id(res_id):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM reservations WHERE id = ?", (res_id,)
        ).fetchone()


def add(client_name, date_, time_, service_type, notes):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO reservations (client_name, date, time, service_type, notes) VALUES (?, ?, ?, ?, ?)",
            (client_name, date_, time_, service_type, notes)
        )


def update(res_id, client_name, date_, time_, service_type, notes):
    with get_conn() as conn:
        conn.execute(
            "UPDATE reservations SET client_name=?, date=?, time=?, service_type=?, notes=? WHERE id=?",
            (client_name, date_, time_, service_type, notes, res_id)
        )


def delete(res_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM reservations WHERE id = ?", (res_id,))
