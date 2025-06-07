import sqlite3
from pathlib import Path

DB_PATH = Path('data/positions.db')


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL,
            combo_type TEXT NOT NULL,
            direction TEXT,
            entry_time TEXT,
            center_strike REAL,
            wing_width REAL,
            short_put_strike REAL,
            short_call_strike REAL,
            entry_credit REAL,
            max_loss REAL,
            current_pnl REAL,
            status TEXT DEFAULT 'OPEN'
        )"""
    )
    conn.commit()
    conn.close()


def get_db_positions():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM positions WHERE status='OPEN'")
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def mark_position_closed(pos_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE positions SET status='CLOSED' WHERE id=?", (pos_id,))
    conn.commit()
    conn.close()
