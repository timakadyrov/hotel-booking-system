"""
db.py
Простая работа с SQLite для хранения комнат, гостей и броней
"""

import sqlite3
from pathlib import Path
from datetime import date

DB_FILE = Path(__file__).parent / "hotel.db"


def init_db(db_path: str = None):
    """Инициализация базы данных (создание таблиц)."""
    db_file = DB_FILE if db_path is None else db_path
    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS rooms (
        room_number TEXT PRIMARY KEY,
        room_type TEXT NOT NULL,
        price_per_night REAL NOT NULL,
        is_occupied INTEGER NOT NULL DEFAULT 0
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS guests (
        guest_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT,
        phone TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        booking_id TEXT PRIMARY KEY,
        guest_id TEXT NOT NULL,
        room_number TEXT NOT NULL,
        check_in_date TEXT NOT NULL,
        check_out_date TEXT NOT NULL,
        status TEXT NOT NULL,
        FOREIGN KEY(guest_id) REFERENCES guests(guest_id),
        FOREIGN KEY(room_number) REFERENCES rooms(room_number)
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        payment_id TEXT PRIMARY KEY,
        booking_id TEXT NOT NULL,
        amount REAL NOT NULL,
        payment_date TEXT,
        payment_method TEXT,
        status TEXT,
        transaction_id TEXT,
        FOREIGN KEY(booking_id) REFERENCES bookings(booking_id)
    )
    """)
    conn.commit()
    conn.close()


def get_connection(db_path: str = None):
    db_file = DB_FILE if db_path is None else db_path
    return sqlite3.connect(str(db_file))
