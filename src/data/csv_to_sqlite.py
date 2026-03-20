"""
csv_to_sqlite.py – Converts hukom_phase0_dataset.csv into an SQLite database.

Creates:
  data/hukom_phase0.db
    ├── cases          (main table with indexes)
    └── cases_fts      (FTS5 full-text search on facts/issues/ruling)

Usage:
  python -m src.data.csv_to_sqlite
"""

import csv
import os
import sqlite3
import sys
import time

from src.data.config import DATASET_OUT

# Bump CSV field limit – legal texts can be very large
csv.field_size_limit(sys.maxsize)

DB_PATH = os.path.join("data", "hukom_phase0.db")

# Schema
CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS cases (
    case_id            TEXT PRIMARY KEY,
    year               INTEGER,
    case_title         TEXT,
    facts              TEXT,
    issues             TEXT,
    ruling             TEXT,
    case_family_id     TEXT,
    family_size        INTEGER,
    is_near_duplicate  INTEGER,
    split_status       TEXT
);
"""

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_year          ON cases(year);",
    "CREATE INDEX IF NOT EXISTS idx_split_status   ON cases(split_status);",
    "CREATE INDEX IF NOT EXISTS idx_family_id      ON cases(case_family_id);",
]

CREATE_FTS = """
CREATE VIRTUAL TABLE IF NOT EXISTS cases_fts USING fts5(
    case_id,
    facts,
    issues,
    ruling,
    content='cases',
    content_rowid='rowid'
);
"""

POPULATE_FTS = """
INSERT INTO cases_fts(case_id, facts, issues, ruling)
    SELECT case_id, facts, issues, ruling FROM cases;
"""

INSERT_ROW = """
INSERT OR REPLACE INTO cases
    (case_id, year, case_title, facts, issues, ruling,
     case_family_id, family_size, is_near_duplicate, split_status)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
"""


def _safe_int(val, default=None):
    """Convert a string to int, returning default on failure."""
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def convert(csv_path: str = DATASET_OUT, db_path: str = DB_PATH):
    """Read the CSV and write it into a fresh SQLite database."""
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"♻️  Removed existing {db_path}")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Pragmas for speed during bulk import
    cur.execute("PRAGMA journal_mode = WAL;")
    cur.execute("PRAGMA synchronous = NORMAL;")
    cur.execute("PRAGMA cache_size = -64000;")  # 64 MB cache

    cur.execute(CREATE_TABLE)

    print(f"📖 Reading {csv_path} ...")
    t0 = time.time()

    rows_inserted = 0
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        batch = []
        for row in reader:
            batch.append((
                row["case_id"],
                _safe_int(row.get("year")),
                row.get("case_title", ""),
                row.get("facts", ""),
                row.get("issues", ""),
                row.get("ruling", ""),
                row.get("case_family_id", ""),
                _safe_int(row.get("family_size")),
                _safe_int(row.get("is_near_duplicate"), 0),
                row.get("split_status", ""),
            ))
            if len(batch) >= 500:
                cur.executemany(INSERT_ROW, batch)
                rows_inserted += len(batch)
                batch.clear()

        if batch:
            cur.executemany(INSERT_ROW, batch)
            rows_inserted += len(batch)

    conn.commit()
    elapsed_insert = time.time() - t0
    print(f"✅ Inserted {rows_inserted:,} rows in {elapsed_insert:.1f}s")

    # Indexes
    print("🔧 Creating indexes ...")
    for idx_sql in CREATE_INDEXES:
        cur.execute(idx_sql)
    conn.commit()

    # FTS
    print("🔍 Building full-text search index ...")
    t1 = time.time()
    cur.execute(CREATE_FTS)
    cur.execute(POPULATE_FTS)
    conn.commit()
    print(f"✅ FTS index built in {time.time() - t1:.1f}s")

    # Verify
    count = cur.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
    db_size_mb = os.path.getsize(db_path) / (1024 * 1024)
    print(f"\n📊 Verification:")
    print(f"   Rows in CSV:    {rows_inserted:,}")
    print(f"   Rows in SQLite: {count:,}")
    print(f"   DB size:        {db_size_mb:.1f} MB")
    print(f"   Match: {'✅ YES' if count == rows_inserted else '❌ NO — MISMATCH!'}")

    conn.close()
    print(f"\n🎉 Database saved to {db_path}")


if __name__ == "__main__":
    convert()
