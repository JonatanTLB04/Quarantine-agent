import os

import psycopg
from psycopg.rows import dict_row


def _conn():
    return psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row, autocommit=True)


def init():
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id SERIAL PRIMARY KEY,
                ts TIMESTAMPTZ NOT NULL DEFAULT now(),
                client TEXT,
                kind TEXT,          -- message | tickets | error
                sender TEXT,
                subject TEXT,
                recipient TEXT,
                decision TEXT,      -- allow | deny | unsure
                category TEXT,      -- phishing | spam | legit | unsure
                why TEXT,
                google_action TEXT,
                tickets TEXT,
                result TEXT,        -- ok | review | observacion | error
                mode TEXT,
                detail TEXT
            )
        """)


def add(**fields):
    cols = list(fields)
    with _conn() as c:
        c.execute(
            f"INSERT INTO logs ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))})",
            [fields[k] for k in cols],
        )


def recent(limit=500):
    with _conn() as c:
        return c.execute("SELECT * FROM logs ORDER BY id DESC LIMIT %s", (limit,)).fetchall()
