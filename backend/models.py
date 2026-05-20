"""Database models and setup for ArtLocal.

Uses PostgreSQL if DATABASE_URL is set (Render), otherwise SQLite (local dev).
"""

import os
import sqlite3
from pathlib import Path

DATABASE_URL = os.environ.get("DATABASE_URL", "")

# ── PostgreSQL mode ──────────────────────────────────────────────────────

if DATABASE_URL:
    import psycopg2
    import psycopg2.extras

    # Render gives postgres:// but psycopg2 needs postgresql://
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    def get_db():
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        return conn

    def init_db():
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                display_name TEXT,
                bio TEXT DEFAULT '',
                is_artist INTEGER DEFAULT 0,
                lat REAL,
                lng REAL,
                created_at TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS listings (
                id SERIAL PRIMARY KEY,
                artist_id INTEGER NOT NULL REFERENCES users(id),
                title TEXT NOT NULL,
                price REAL NOT NULL,
                medium TEXT,
                dimensions TEXT,
                description TEXT DEFAULT '',
                image_url TEXT NOT NULL,
                image_public_id TEXT,
                lat REAL NOT NULL,
                lng REAL NOT NULL,
                is_sold INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                sender_id INTEGER NOT NULL REFERENCES users(id),
                receiver_id INTEGER NOT NULL REFERENCES users(id),
                listing_id INTEGER REFERENCES listings(id),
                body TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS follows (
                id SERIAL PRIMARY KEY,
                follower_id INTEGER NOT NULL REFERENCES users(id),
                artist_id INTEGER NOT NULL REFERENCES users(id),
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(follower_id, artist_id)
            );

            CREATE TABLE IF NOT EXISTS favorites (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                listing_id INTEGER NOT NULL REFERENCES listings(id),
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(user_id, listing_id)
            );

            CREATE INDEX IF NOT EXISTS idx_listings_artist ON listings(artist_id);
            CREATE INDEX IF NOT EXISTS idx_listings_sold ON listings(is_sold);
            CREATE INDEX IF NOT EXISTS idx_messages_receiver ON messages(receiver_id);
            CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id);
            CREATE INDEX IF NOT EXISTS idx_follows_artist ON follows(artist_id);
            CREATE INDEX IF NOT EXISTS idx_favorites_user ON favorites(user_id);
        """)
        conn.commit()
        conn.close()

# ── SQLite mode (local development) ─────────────────────────────────────

else:
    DB_PATH = Path(__file__).parent.parent / "data" / "artlocal.db"

    def get_db():
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def init_db():
        conn = get_db()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                display_name TEXT,
                bio TEXT DEFAULT '',
                is_artist INTEGER DEFAULT 0,
                lat REAL,
                lng REAL,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                artist_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                price REAL NOT NULL,
                medium TEXT,
                dimensions TEXT,
                description TEXT DEFAULT '',
                image_url TEXT NOT NULL,
                image_public_id TEXT,
                lat REAL NOT NULL,
                lng REAL NOT NULL,
                is_sold INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (artist_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                listing_id INTEGER,
                body TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (sender_id) REFERENCES users(id),
                FOREIGN KEY (receiver_id) REFERENCES users(id),
                FOREIGN KEY (listing_id) REFERENCES listings(id)
            );

            CREATE TABLE IF NOT EXISTS follows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                follower_id INTEGER NOT NULL,
                artist_id INTEGER NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (follower_id) REFERENCES users(id),
                FOREIGN KEY (artist_id) REFERENCES users(id),
                UNIQUE(follower_id, artist_id)
            );

            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                listing_id INTEGER NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (listing_id) REFERENCES listings(id),
                UNIQUE(user_id, listing_id)
            );

            CREATE INDEX IF NOT EXISTS idx_listings_artist ON listings(artist_id);
            CREATE INDEX IF NOT EXISTS idx_listings_sold ON listings(is_sold);
            CREATE INDEX IF NOT EXISTS idx_messages_receiver ON messages(receiver_id);
            CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id);
            CREATE INDEX IF NOT EXISTS idx_follows_artist ON follows(artist_id);
            CREATE INDEX IF NOT EXISTS idx_favorites_user ON favorites(user_id);
        """)
        conn.close()


# ── Helper for portable queries ──────────────────────────────────────────

def query(conn, sql, params=None):
    """Execute a query and return list of dicts."""
    if DATABASE_URL:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params or ())
        try:
            rows = cur.fetchall()
            return [dict(r) for r in rows]
        except psycopg2.ProgrammingError:
            return []
    else:
        cur = conn.execute(sql, params or ())
        rows = cur.fetchall()
        return [dict(r) for r in rows]


def query_one(conn, sql, params=None):
    """Execute a query and return one dict or None."""
    rows = query(conn, sql, params)
    return rows[0] if rows else None


def execute(conn, sql, params=None):
    """Execute an INSERT/UPDATE/DELETE. Returns lastrowid for inserts."""
    if DATABASE_URL:
        cur = conn.cursor()
        if sql.strip().upper().startswith("INSERT") and "RETURNING" not in sql.upper():
            sql = sql.rstrip().rstrip(";") + " RETURNING id"
        cur.execute(sql, params or ())
        if sql.strip().upper().startswith("INSERT"):
            row = cur.fetchone()
            return row[0] if row else None
        return None
    else:
        cur = conn.execute(sql, params or ())
        return cur.lastrowid
