# -*- coding: utf-8 -*-
"""
database - historial de escaneos en SQLite (stdlib, cero deps).

Guarda cada escaneo y sus redes para que puedas ver como cambian las redes
a tu alrededor con el tiempo (una red nueva que aparece, una que se va, como
sube/baja la senal). Archivo: data/radarwifi.db
"""
import os
import json
import sqlite3
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "..", "data", "radarwifi.db")
_lock = threading.Lock()


def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _lock, _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS scans (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            ts      REAL NOT NULL,
            mode    TEXT,
            count   INTEGER
        );
        CREATE TABLE IF NOT EXISTS networks (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id INTEGER,
            ssid    TEXT, bssid TEXT, signal INTEGER, rssi INTEGER,
            channel INTEGER, band TEXT, auth TEXT, enc TEXT,
            vendor  TEXT, open INTEGER,
            FOREIGN KEY(scan_id) REFERENCES scans(id)
        );
        CREATE INDEX IF NOT EXISTS idx_net_bssid ON networks(bssid);
        """)


def save_scan(ts: float, mode: str, networks: list) -> int:
    """Guarda un escaneo. `ts` viene del caller (los scripts no pueden usar time aqui)."""
    with _lock, _conn() as c:
        cur = c.execute("INSERT INTO scans(ts, mode, count) VALUES (?,?,?)",
                        (ts, mode, len(networks)))
        scan_id = cur.lastrowid
        c.executemany(
            "INSERT INTO networks(scan_id,ssid,bssid,signal,rssi,channel,band,auth,enc,vendor,open) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [(scan_id, n.get("ssid"), n.get("bssid"), n.get("signal"), n.get("rssi"),
              n.get("channel"), n.get("band"), n.get("auth"), n.get("enc"),
              n.get("vendor"), 1 if n.get("open") else 0) for n in networks])
        return scan_id


def recent_scans(limit: int = 25) -> list:
    with _lock, _conn() as c:
        rows = c.execute("SELECT * FROM scans ORDER BY ts DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]


def networks_for_scan(scan_id: int) -> list:
    with _lock, _conn() as c:
        rows = c.execute("SELECT * FROM networks WHERE scan_id=?", (scan_id,)).fetchall()
        return [dict(r) for r in rows]


def history_for_bssid(bssid: str, limit: int = 100) -> list:
    """Serie temporal de senal de un AP concreto (para graficar su evolucion)."""
    with _lock, _conn() as c:
        rows = c.execute(
            "SELECT s.ts, n.signal, n.rssi, n.channel FROM networks n "
            "JOIN scans s ON s.id=n.scan_id WHERE n.bssid=? ORDER BY s.ts DESC LIMIT ?",
            (bssid.lower(), limit)).fetchall()
        return [dict(r) for r in rows]


def stats() -> dict:
    with _lock, _conn() as c:
        total = c.execute("SELECT COUNT(*) FROM scans").fetchone()[0]
        uniq = c.execute("SELECT COUNT(DISTINCT bssid) FROM networks").fetchone()[0]
        return {"total_scans": total, "unique_networks": uniq}
