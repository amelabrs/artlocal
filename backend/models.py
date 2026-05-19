"""Database models and setup for ArtLocal."""

import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "artlocal.db"


def get_db():
    """Get a database connection."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create tables if they don't exist."""
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

        CREATE INDEX IF NOT EXISTS idx_listings_artist ON listings(artist_id);
        CREATE INDEX IF NOT EXISTS idx_listings_sold ON listings(is_sold);
    """)
    conn.close()
