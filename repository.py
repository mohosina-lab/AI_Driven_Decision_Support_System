"""Local Production records, seeded from synthetic JSON and updated atomically."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3


class RevisionConflict(Exception):
    pass


def connect(path):
    return sqlite3.connect(str(path), timeout=10)


def initialise(path, seed_path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    seeds = json.loads(Path(seed_path).read_text())
    with connect(path) as db:
        db.execute('CREATE TABLE IF NOT EXISTS orders (order_id TEXT PRIMARY KEY, payload TEXT NOT NULL, revision INTEGER NOT NULL)')
        db.executemany('INSERT OR IGNORE INTO orders VALUES (?, ?, 1)', [(order['order_id'], json.dumps(order)) for order in seeds])


def list_orders(path):
    with connect(path) as db:
        rows = db.execute('SELECT payload, revision FROM orders ORDER BY order_id').fetchall()
    return [(json.loads(payload), revision) for payload, revision in rows]


def get_order(path, order_id):
    with connect(path) as db:
        row = db.execute('SELECT payload, revision FROM orders WHERE order_id = ?', (order_id,)).fetchone()
    if row is None:
        return None
    return json.loads(row[0]), row[1]


def update_order(path, order, expected_revision):
    updated = dict(order)
    updated['last_updated'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
    with connect(path) as db:
        cursor = db.execute('UPDATE orders SET payload = ?, revision = revision + 1 WHERE order_id = ? AND revision = ?',
                            (json.dumps(updated), order['order_id'], expected_revision))
        if cursor.rowcount != 1:
            raise RevisionConflict('This order changed in another session. Reload the Production record before saving again.')
    return updated
