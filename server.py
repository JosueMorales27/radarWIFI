# -*- coding: utf-8 -*-
"""
radarWIFI - servidor local (cero dependencias, solo stdlib de Python)
--------------------------------------------------------------------
- Escanea las redes WiFi REALES a tu alrededor usando `netsh` (Windows).
- Si no hay adaptador WiFi, arranca en modo SIMULACION para que veas el radar.
- TODO corre en tu maquina. Nada sale a internet. Nadie recibe tus datos.

Autor: hecho para Josue con Claude Code.
"""
import http.server
import socketserver
import subprocess
import json
import re
import os
import sys
import math
import time
import random
import webbrowser
import threading
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = 8777


# ----------------------------------------------------------------------
#  Decodificar la salida de netsh (Windows en espanol usa codepage OEM)
# ----------------------------------------------------------------------
def _decode(raw: bytes) -> str:
    for enc in ("utf-8", "cp1252", "cp850", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _run(cmd):
    try:
        out = subprocess.run(
            cmd, capture_output=True, shell=False, timeout=25
        )
        return _decode(out.stdout)
    except Exception as e:
        return ""


def has_wifi_adapter() -> bool:
    txt = _run(["netsh", "wlan", "show", "interfaces"]).lower()
    if not txt:
        return False
    # frases que indican que NO hay adaptador (es/en)
    if "no hay ninguna interfaz" in txt or "there is no wireless interface" in txt:
        return False
    # si menciona un adaptador/estado, si hay
    return ("nombre" in txt or "name" in txt or "estado" in txt or "state" in txt)


# ----------------------------------------------------------------------
#  Parseo robusto de `netsh wlan show networks mode=bssid` (es / en)
# ----------------------------------------------------------------------
RE_SSID = re.compile(r"^\s*SSID\s+\d+\s*:\s*(.*)$", re.IGNORECASE)
RE_BSSID = re.compile(r"BSSID\s+\d+\s*:\s*([0-9a-fA-F:]{17})", re.IGNORECASE)
RE_SIGNAL = re.compile(r":\s*(\d{1,3})\s*%")
RE_CHANNEL = re.compile(r"(?:Canal|Channel)\D*?(\d{1,3})", re.IGNORECASE)
RE_AUTH = re.compile(r"(?:Autentic\w*|Authentic\w*)\s*:\s*(.*)", re.IGNORECASE)
RE_ENC = re.compile(r"(?:Cifrado|Encryption)\s*:\s*(.*)", re.IGNORECASE)
RE_RADIO = re.compile(r"(?:Tipo de radio|Radio type)\s*:\s*(.*)", re.IGNORECASE)


def band_from_channel(ch):
    try:
        ch = int(ch)
    except (TypeError, ValueError):
        return "?"
    if 1 <= ch <= 14:
        return "2.4 GHz"
    if 32 <= ch <= 196:
        return "5 GHz"
    if ch >= 197:
        return "6 GHz"
    return "?"


def is_open(auth: str) -> bool:
    a = (auth or "").strip().lower()
    return a in ("", "abierta", "open", "abierto") or "open" in a and "wpa" not in a


def scan_real():
    txt = _run(["netsh", "wlan", "show", "networks", "mode=bssid"])
    nets = []
    current_ssid = None
    current_meta = {}
    ap = None

    for line in txt.splitlines():
        m = RE_SSID.match(line)
        if m:
            current_ssid = m.group(1).strip() or "<oculta>"
            current_meta = {}
            continue

        mb = RE_BSSID.search(line)
        if mb:
            ap = {
                "ssid": current_ssid or "<oculta>",
                "bssid": mb.group(1).lower(),
                "signal": 0,
                "channel": None,
                "band": "?",
                "auth": current_meta.get("auth", "?"),
                "enc": current_meta.get("enc", "?"),
                "radio": "?",
                "open": False,
            }
            nets.append(ap)
            continue

        ma = RE_AUTH.search(line)
        if ma:
            val = ma.group(1).strip()
            current_meta["auth"] = val
            if ap is not None and ap["auth"] == "?":
                ap["auth"] = val
            continue

        me = RE_ENC.search(line)
        if me and ap is not None:
            ap["enc"] = me.group(1).strip()
            continue

        if ap is not None:
            ms = RE_SIGNAL.search(line)
            if ms and ap["signal"] == 0:
                ap["signal"] = int(ms.group(1))
                continue
            mc = RE_CHANNEL.search(line)
            if mc and ap["channel"] is None:
                ap["channel"] = int(mc.group(1))
                ap["band"] = band_from_channel(ap["channel"])
                continue
            mr = RE_RADIO.search(line)
            if mr:
                ap["radio"] = mr.group(1).strip()

    for ap in nets:
        ap["open"] = is_open(ap.get("auth"))
    return nets


# ----------------------------------------------------------------------
#  Modo simulacion (cuando no hay adaptador WiFi)
# ----------------------------------------------------------------------
_SIM_NAMES = [
    ("INFINITUM_A4F2", "WPA2-Personal"),
    ("TP-LINK_5G", "WPA2-Personal"),
    ("IZZI-8830", "WPA2-Personal"),
    ("Totalplay-2.4G", "WPA3-Personal"),
    ("MEGACABLE_1122", "WPA2-Personal"),
    ("HP-Setup", ""),            # abierta
    ("iPhone de Ana", "WPA2-Personal"),
    ("<oculta>", "WPA2-Personal"),
    ("CFE_Publico", ""),         # abierta
    ("NETGEAR_5G", "WPA2-Personal"),
    ("Xfinity", ""),             # abierta
]


def scan_sim():
    rng = random.Random()
    nets = []
    picked = rng.sample(_SIM_NAMES, k=rng.randint(6, len(_SIM_NAMES)))
    for name, auth in picked:
        ch = rng.choice([1, 6, 11, 36, 44, 149, 157])
        nets.append({
            "ssid": name,
            "bssid": ":".join("%02x" % rng.randint(0, 255) for _ in range(6)),
            "signal": rng.randint(18, 99),
            "channel": ch,
            "band": band_from_channel(ch),
            "auth": auth or "Abierta",
            "enc": "CCMP" if auth else "Ninguno",
            "radio": "802.11ac" if ch >= 36 else "802.11n",
            "open": auth == "",
        })
    return nets


# ----------------------------------------------------------------------
#  Modo SENSING (RuView) - replica lo que hace el repo ruvnet/ruview
#  usando CSI de placas ESP32. SIN ese hardware, el repo oficial corre
#  en modo MOCK (MOCK_HARDWARE=true) con datos simulados. Aqui hacemos
#  lo mismo: presencia, esqueleto 17 puntos, vitales, caidas -> SIMULADO.
#  El dia que conectes ESP32-CSI, se sustituye esta funcion por la lectura
#  real y todo lo demas (UI, esqueletos, vitales) sigue igual.
# ----------------------------------------------------------------------
def has_csi_hardware() -> bool:
    # No hay soporte de CSI en Windows/netsh. Reservado para futuro ESP32.
    return False


# 17 keypoints estilo COCO (cabeza -> pies) en coords normalizadas [-1..1]
# relativas al centro de la persona. Postura "de pie" base.
_POSE_BASE = [
    (0.00, -0.90),  # 0 nariz
    (-0.04, -0.94), (0.04, -0.94),      # 1,2 ojos
    (-0.08, -0.92), (0.08, -0.92),      # 3,4 orejas
    (-0.18, -0.62), (0.18, -0.62),      # 5,6 hombros
    (-0.26, -0.30), (0.26, -0.30),      # 7,8 codos
    (-0.30, 0.02), (0.30, 0.02),        # 9,10 munecas
    (-0.12, -0.02), (0.12, -0.02),      # 11,12 caderas
    (-0.14, 0.44), (0.14, 0.44),        # 13,14 rodillas
    (-0.15, 0.88), (0.15, 0.88),        # 15,16 tobillos
]

_ACTIVITIES = ["de pie", "caminando", "sentado", "quieto"]


def sensing_frame():
    """Genera un frame simulado coherente en el tiempo (usa time.time())."""
    t = time.time()
    live = has_csi_hardware()

    # cuantas personas "hay" (varia lento)
    n = 1 + int((math.sin(t * 0.07) + 1))  # 1..2 personas, cambia lento
    persons = []
    for i in range(n):
        ph = i * 2.3
        # posicion en el cuarto [0..1] con deriva lenta (no teletransporta)
        px = 0.5 + 0.28 * math.sin(t * 0.15 + ph)
        py = 0.5 + 0.22 * math.cos(t * 0.11 + ph * 1.7)
        moving = abs(math.sin(t * 0.15 + ph)) > 0.35
        act = "caminando" if moving else _ACTIVITIES[(i + int(t * 0.05)) % len(_ACTIVITIES)]

        # vitales realistas con variabilidad (respiracion ~12-18, pulso ~62-88)
        breathing = round(15 + 3 * math.sin(t * 0.9 + ph), 1)
        heart = round(74 + 10 * math.sin(t * 0.5 + ph) + 2 * math.sin(t * 3 + ph), 0)

        # esqueleto: base + micro-movimiento (respira, se balancea)
        sway = 0.03 * math.sin(t * 1.3 + ph)
        breathe = 0.015 * math.sin(t * (breathing / 60.0) * 2 * math.pi)
        kp = []
        for (kx, ky) in _POSE_BASE:
            jitter = 0.01 * math.sin(t * 2 + kx * 7 + ph)
            kp.append([round(kx + sway + jitter, 3), round(ky - breathe, 3)])

        persons.append({
            "id": i + 1,
            "x": round(px, 3),
            "y": round(py, 3),
            "activity": act,
            "moving": moving,
            "heart_rate": int(heart),
            "breathing_rate": breathing,
            "keypoints": kp,
            "confidence": round(0.72 + 0.2 * abs(math.sin(t + ph)), 2),
        })

    # caida: evento raro (ventana corta cada ~90s)
    fall = (int(t) % 90) < 2 and n > 0
    motion = int(min(100, sum(60 if p["moving"] else 15 for p in persons)))

    return {
        "mode": "EN VIVO" if live else "SIMULADO",
        "hardware": live,
        "presence": n > 0,
        "person_count": n,
        "motion_level": motion,
        "fall_detected": bool(fall),
        "persons": persons,
    }


# ----------------------------------------------------------------------
#  HTTP handler
# ----------------------------------------------------------------------
class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass  # silencio

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            fp = os.path.join(HERE, "index.html")
            with open(fp, "rb") as f:
                self._send(200, f.read(), "text/html; charset=utf-8")
            return
        if path in ("/sensing", "/sensing.html"):
            fp = os.path.join(HERE, "sensing.html")
            with open(fp, "rb") as f:
                self._send(200, f.read(), "text/html; charset=utf-8")
            return
        if path == "/api/sensing":
            self._send(200, json.dumps(sensing_frame()))
            return
        if path == "/api/scan":
            live = has_wifi_adapter()
            nets = scan_real() if live else []
            mode = "EN VIVO"
            if not nets:
                nets = scan_sim()
                mode = "SIMULACION"
            nets.sort(key=lambda n: n["signal"], reverse=True)
            self._send(200, json.dumps({"mode": mode, "networks": nets}))
            return
        if path == "/favicon.ico":
            fp = os.path.join(HERE, "radar.ico")
            if os.path.exists(fp):
                with open(fp, "rb") as f:
                    self._send(200, f.read(), "image/x-icon")
                return
        self._send(404, json.dumps({"error": "not found"}))


def main():
    os.chdir(HERE)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("127.0.0.1", PORT), Handler) as httpd:
        url = f"http://127.0.0.1:{PORT}/"
        print("=" * 52)
        print("  radarWIFI corriendo en", url)
        print("  Todo local. Cierra esta ventana para apagarlo.")
        print("=" * 52)
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nApagando radarWIFI. Hasta luego, Josue.")


if __name__ == "__main__":
    main()
