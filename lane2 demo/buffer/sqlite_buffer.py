"""
SQLite-backed durable buffer for telemetry data (simplified version).

No retry logic, no error logs — clean, minimal, future-proof.
"""
import sqlite3
import json
import time
from typing import Dict, Any, List, Optional
from pathlib import Path

DB_PATH = Path(__file__).parent / "bridge_buffer.db"


def init_db() -> None:
    """Create buffer table if not exists."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS buffer (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER NOT NULL,
            source TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            forwarded INTEGER DEFAULT 0
        )
    """)
    
    # Add forwarded column if it doesn't exist (for existing databases)
    try:
        cursor.execute("ALTER TABLE buffer ADD COLUMN forwarded INTEGER DEFAULT 0")
        # Update any existing NULL values to 0
        cursor.execute("UPDATE buffer SET forwarded = 0 WHERE forwarded IS NULL")
        conn.commit()
    except sqlite3.OperationalError:
        # Column already exists, but ensure no NULL values
        cursor.execute("UPDATE buffer SET forwarded = 0 WHERE forwarded IS NULL")
        conn.commit()
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_buffer_ts ON buffer(ts)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_buffer_forwarded ON buffer(forwarded)
    """)
    
    conn.commit()
    conn.close()


def enqueue_record(source: str, payload: dict, ts: Optional[int] = None) -> None:
    """Insert JSON-serialized payload into the buffer."""
    ts = ts or int(time.time())
    payload_json = json.dumps(payload)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Explicitly set forwarded=0 for new records
    cursor.execute("""
        INSERT INTO buffer (ts, source, payload_json, forwarded)
        VALUES (?, ?, ?, 0)
    """, (ts, source, payload_json))
    
    conn.commit()
    conn.close()


def dequeue_batch(limit: int = 100, only_unforwarded: bool = True) -> List[Dict[str, Any]]:
    """
    Return oldest rows as list of dicts.
    
    Args:
        limit: Maximum number of rows to return
        only_unforwarded: If True, only return rows that haven't been forwarded yet
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if only_unforwarded:
        # Handle NULL values (for rows created before forwarded column existed)
        cursor.execute("""
            SELECT id, ts, source, payload_json, COALESCE(forwarded, 0) as forwarded
            FROM buffer
            WHERE COALESCE(forwarded, 0) = 0
            ORDER BY ts ASC, id ASC
            LIMIT ?
        """, (limit,))
    else:
        cursor.execute("""
            SELECT id, ts, source, payload_json, COALESCE(forwarded, 0) as forwarded
            FROM buffer
            ORDER BY ts ASC, id ASC
            LIMIT ?
        """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            "id": row[0],
            "ts": row[1],
            "source": row[2],
            "payload": json.loads(row[3]),
            "forwarded": row[4] if len(row) > 4 else 0,
        }
        for row in rows
    ]


def mark_success(ids: List[int]) -> None:
    """Delete successfully processed rows."""
    if not ids:
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    placeholders = ",".join("?" * len(ids))
    cursor.execute(f"DELETE FROM buffer WHERE id IN ({placeholders})", ids)
    
    conn.commit()
    conn.close()


def mark_forwarded(ids: List[int]) -> None:
    """Mark rows as forwarded (but keep them in buffer for reinjection)."""
    if not ids:
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    placeholders = ",".join("?" * len(ids))
    cursor.execute(f"UPDATE buffer SET forwarded = 1 WHERE id IN ({placeholders})", ids)
    
    rows_updated = cursor.rowcount
    conn.commit()
    conn.close()
    
    # Log if update didn't work
    if rows_updated != len(ids):
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"mark_forwarded: Expected to update {len(ids)} rows, but updated {rows_updated}")


def mark_unforwarded(ids: List[int]) -> None:
    """Mark rows as unforwarded (for reinjection)."""
    if not ids:
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    placeholders = ",".join("?" * len(ids))
    cursor.execute(f"UPDATE buffer SET forwarded = 0 WHERE id IN ({placeholders})", ids)
    
    conn.commit()
    conn.close()


def prune_older_than(seconds: int) -> None:
    """Permanently delete rows older than the retention window."""
    cutoff = int(time.time()) - seconds
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM buffer WHERE ts < ?", (cutoff,))
    
    conn.commit()
    conn.close()


def get_buffer_depth() -> int:
    """Return total number of buffered rows."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM buffer")
    (count,) = cursor.fetchone()
    
    conn.close()
    return count
