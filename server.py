# -*- coding: utf-8 -*-
"""
radarWIFI PRO - servidor local (stdlib de Python; nmap/scapy opcionales).
--------------------------------------------------------------------------
Interfaz estilo Kali para explorar las redes WiFi a tu alrededor:
  - Radar animado con fabricante (OUI), filtros y heatmap de canales.
  - Integracion nmap (descubrir hosts, puertos, servicios, SO).
  - Terminal de recon con lista blanca (aprende nmap, ping, arp, iw...).
  - Historial en SQLite + exportar CSV/JSON/HTML.
  - WiFi sensing estilo RuView (ver personas sin camara) - simulado sin ESP32-CSI.
  - Modulos activos (deauth ligero / handshakes) SOLO en Linux + modo monitor.

TODO corre en 127.0.0.1. Nada sale a internet. Autor: para Josue, con Claude Code.
"""
import os
import sys
import json
import time
import threading
import webbrowser
import http.server
import socketserver
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from core import platform_detect as plat   # noqa: E402
from core import scanner                    # noqa: E402
from core import nmap_integration as nmapi  # noqa: E402
from core import sensing                     # noqa: E402
from core import database as db              # noqa: E402
from core import export                      # noqa: E402
from core import terminal                    # noqa: E402
from core import attacks                     # noqa: E402

PORT = 8777
_LAST_SCAN = {"mode": "?", "networks": []}   # cache para exportar


# ----------------------------------------------------------------------
#  HTTP handler
# ----------------------------------------------------------------------
class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    # -- helpers --------------------------------------------------------
    def _send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False))

    def _file(self, name, ctype):
        fp = os.path.join(HERE, name)
        if not os.path.exists(fp):
            return self._json({"error": "no encontrado: " + name}, 404)
        with open(fp, "rb") as f:
            self._send(200, f.read(), ctype)

    def _body_json(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(n) if n else b"{}"
            return json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            return {}

    # -- GET ------------------------------------------------------------
    def do_GET(self):
        path = urlparse(self.path).path
        qs = parse_qs(urlparse(self.path).query)

        if path in ("/", "/index.html"):
            return self._file("index.html", "text/html; charset=utf-8")
        if path in ("/sensing", "/sensing.html"):
            return self._file("index.html", "text/html; charset=utf-8")

        if path == "/api/capabilities":
            return self._json(plat.capabilities())

        if path == "/api/scan":
            mode, nets = scanner.scan()
            _LAST_SCAN["mode"], _LAST_SCAN["networks"] = mode, nets
            try:
                db.save_scan(time.time(), mode, nets)
            except Exception:
                pass
            return self._json({"mode": mode, "networks": nets})

        if path == "/api/sensing":
            return self._json(sensing.sensing_frame())

        if path == "/api/localinfo":
            return self._json(scanner.local_info())

        if path == "/api/neighbors":
            try:
                return self._json({"hosts": scanner.arp_neighbors()})
            except Exception as e:
                return self._json({"hosts": [], "error": str(e)})

        if path == "/api/history":
            try:
                return self._json({"scans": db.recent_scans(), "stats": db.stats()})
            except Exception as e:
                return self._json({"scans": [], "stats": {}, "error": str(e)})

        if path == "/api/terminal/allowed":
            return self._json({"allowed": terminal.allowed_commands()})

        if path == "/api/attack/interfaces":
            return self._json(attacks.list_interfaces())

        if path == "/api/export":
            fmt = (qs.get("fmt", ["json"])[0])
            nets = _LAST_SCAN["networks"]
            meta = {"modo": _LAST_SCAN["mode"], "redes": len(nets),
                    "so": plat.os_name(), "generado": time.strftime("%Y-%m-%d %H:%M:%S")}
            text, ctype, fname = export.render(fmt, nets, meta)
            return self._send(200, text, ctype,
                              extra={"Content-Disposition": 'attachment; filename="%s"' % fname})

        if path == "/favicon.ico":
            return self._file("radar.ico", "image/x-icon")

        self._json({"error": "not found"}, 404)

    # -- POST -----------------------------------------------------------
    def do_POST(self):
        path = urlparse(self.path).path
        body = self._body_json()

        if path == "/api/nmap":
            return self._json(nmapi.scan(body.get("target", ""),
                                         body.get("profile", "quick")))

        if path == "/api/terminal":
            return self._json(terminal.run(body.get("command", "")))

        if path == "/api/attack/monitor/start":
            return self._json(attacks.monitor_start(body.get("iface", "")))
        if path == "/api/attack/monitor/stop":
            return self._json(attacks.monitor_stop(body.get("iface", "")))
        if path == "/api/attack/deauth":
            return self._json(attacks.deauth(
                body.get("iface", ""), body.get("bssid", ""),
                body.get("count", 5), body.get("client"), body.get("confirm", False)))
        if path == "/api/attack/handshake":
            return self._json(attacks.capture_handshake(
                body.get("iface", ""), body.get("bssid", ""),
                body.get("channel", 1), body.get("seconds", 30)))

        self._json({"error": "not found"}, 404)


def main():
    os.chdir(HERE)
    try:
        db.init_db()
    except Exception as e:
        print("  (aviso) no se pudo iniciar la DB de historial:", e)

    caps = plat.capabilities()
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("127.0.0.1", PORT), Handler) as httpd:
        url = "http://127.0.0.1:%d/" % PORT
        print("=" * 60)
        print("  radarWIFI PRO corriendo en", url)
        print("  SO: %s | nmap: %s | monitor/deauth: %s" % (
            caps["os"], "si" if caps["nmap"] else "no",
            "si" if caps["monitor_mode"] else "no (solo Linux)"))
        print("  Todo local en 127.0.0.1. Cierra esta ventana para apagarlo.")
        print("=" * 60)
        if not os.environ.get("RADARWIFI_NOOPEN"):
            threading.Timer(1.0, lambda: webbrowser.open(url)).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nApagando radarWIFI PRO. Hasta luego, Josue.")


if __name__ == "__main__":
    main()
