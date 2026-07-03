# -*- coding: utf-8 -*-
"""
scanner - escaneo de redes WiFi cross-platform.

    Windows -> netsh wlan show networks mode=bssid
    Linux   -> nmcli (preferido) -> iwlist (fallback) -> scapy (si hay monitor)
    Sin adaptador o sin permisos -> modo SIMULACION (para ver la UI igual)

Cada red devuelta es un dict uniforme:
    ssid, bssid, signal(0-100), rssi(dBm aprox), channel, band, auth, enc,
    radio, open(bool), vendor
"""
import re
import socket
import subprocess

from . import oui
from . import platform_detect as plat


# ----------------------------------------------------------------------
#  utilidades
# ----------------------------------------------------------------------
def _decode(raw: bytes) -> str:
    for enc in ("utf-8", "cp1252", "cp850", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _run(cmd, timeout=25):
    try:
        out = subprocess.run(cmd, capture_output=True, shell=False, timeout=timeout)
        return _decode(out.stdout)
    except Exception:
        return ""


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


def signal_to_rssi(pct):
    """Aproxima % de senal de Windows/nmcli a dBm (rango tipico -30..-90)."""
    try:
        pct = max(0, min(100, int(pct)))
    except (TypeError, ValueError):
        return None
    return round(-90 + (pct / 100.0) * 60)  # 0%=-90dBm, 100%=-30dBm


def rssi_to_distance(rssi):
    """
    Distancia ESTIMADA en metros con el modelo log-distance path loss:
        d = 10 ^ ((TxPower - RSSI) / (10 * n))
    TxPower = RSSI de referencia a 1 m (~-40 dBm para un AP), n = exponente de
    perdida (2.7 indoor tipico). OJO: es una ESTIMACION burda (paredes, antenas
    y multipath la afectan), pero da una idea util de cerca/lejos.
    """
    try:
        rssi = float(rssi)
    except (TypeError, ValueError):
        return None
    tx_power, n = -40.0, 2.7
    d = 10 ** ((tx_power - rssi) / (10 * n))
    return round(max(0.4, min(d, 150.0)), 1)


def is_open(auth: str) -> bool:
    a = (auth or "").strip().lower()
    if not a or a in ("abierta", "open", "abierto", "none", "--", "ninguno"):
        return True
    return "open" in a and "wpa" not in a and "wep" not in a


def _finish(ap):
    ap["open"] = is_open(ap.get("auth"))
    ap["vendor"] = oui.vendor(ap.get("bssid", ""))
    if ap.get("rssi") is None:
        ap["rssi"] = signal_to_rssi(ap.get("signal", 0))
    ap["distance_m"] = rssi_to_distance(ap.get("rssi"))
    return ap


# ----------------------------------------------------------------------
#  WINDOWS - netsh
# ----------------------------------------------------------------------
RE_SSID = re.compile(r"^\s*SSID\s+\d+\s*:\s*(.*)$", re.IGNORECASE)
RE_BSSID = re.compile(r"BSSID\s+\d+\s*:\s*([0-9a-fA-F:]{17})", re.IGNORECASE)
RE_SIGNAL = re.compile(r":\s*(\d{1,3})\s*%")
RE_CHANNEL = re.compile(r"(?:Canal|Channel)\D*?(\d{1,3})", re.IGNORECASE)
RE_AUTH = re.compile(r"(?:Autentic\w*|Authentic\w*)\s*:\s*(.*)", re.IGNORECASE)
RE_ENC = re.compile(r"(?:Cifrado|Encryption)\s*:\s*(.*)", re.IGNORECASE)
RE_RADIO = re.compile(r"(?:Tipo de radio|Radio type)\s*:\s*(.*)", re.IGNORECASE)


def _scan_windows():
    txt = _run(["netsh", "wlan", "show", "networks", "mode=bssid"])
    nets, current_ssid, current_meta, ap = [], None, {}, None
    for line in txt.splitlines():
        m = RE_SSID.match(line)
        if m:
            current_ssid = m.group(1).strip() or "<oculta>"
            current_meta = {}
            continue
        mb = RE_BSSID.search(line)
        if mb:
            ap = {"ssid": current_ssid or "<oculta>", "bssid": mb.group(1).lower(),
                  "signal": 0, "rssi": None, "channel": None, "band": "?",
                  "auth": current_meta.get("auth", "?"), "enc": current_meta.get("enc", "?"),
                  "radio": "?"}
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
    return [_finish(a) for a in nets]


# ----------------------------------------------------------------------
#  LINUX - nmcli (preferido, no necesita root)
# ----------------------------------------------------------------------
def _scan_nmcli():
    # -t = terse (separado por :), campos escapados con backslash
    txt = _run(["nmcli", "-t", "-f", "SSID,BSSID,CHAN,SIGNAL,SECURITY,FREQ",
                "dev", "wifi", "list", "--rescan", "yes"])
    if not txt.strip():
        return []
    nets = []
    for line in txt.splitlines():
        # el BSSID trae ':' escapados como '\:' -> partir cuidando eso
        parts = re.split(r"(?<!\\):", line)
        parts = [p.replace("\\:", ":") for p in parts]
        if len(parts) < 5:
            continue
        ssid, bssid, chan, signal, security = parts[0], parts[1], parts[2], parts[3], parts[4]
        freq = parts[5] if len(parts) > 5 else ""
        try:
            ch = int(chan)
        except ValueError:
            ch = None
        band = band_from_channel(ch)
        if band == "?" and "5" in freq[:1]:
            band = "5 GHz"
        nets.append(_finish({
            "ssid": ssid or "<oculta>", "bssid": bssid.lower(),
            "signal": int(signal) if signal.isdigit() else 0, "rssi": None,
            "channel": ch, "band": band,
            "auth": security or "Abierta", "enc": security or "Ninguno",
            "radio": "802.11",
        }))
    return nets


# ----------------------------------------------------------------------
#  LINUX - iwlist (fallback, suele necesitar sudo)
# ----------------------------------------------------------------------
def _default_iface_linux():
    txt = _run(["iw", "dev"])
    m = re.search(r"Interface\s+(\S+)", txt)
    return m.group(1) if m else "wlan0"


def _scan_iwlist():
    iface = _default_iface_linux()
    txt = _run(["iwlist", iface, "scan"])
    if not txt.strip():
        return []
    nets, ap = [], None
    for line in txt.splitlines():
        line = line.strip()
        mb = re.search(r"Address:\s*([0-9A-Fa-f:]{17})", line)
        if mb:
            if ap:
                nets.append(_finish(ap))
            ap = {"ssid": "<oculta>", "bssid": mb.group(1).lower(), "signal": 0,
                  "rssi": None, "channel": None, "band": "?", "auth": "?",
                  "enc": "?", "radio": "802.11"}
            continue
        if ap is None:
            continue
        me = re.search(r'ESSID:"(.*)"', line)
        if me:
            ap["ssid"] = me.group(1) or "<oculta>"
        mc = re.search(r"Channel:?\s*(\d+)", line)
        if mc:
            ap["channel"] = int(mc.group(1))
            ap["band"] = band_from_channel(ap["channel"])
        ms = re.search(r"Signal level=(-?\d+)\s*dBm", line)
        if ms:
            ap["rssi"] = int(ms.group(1))
            ap["signal"] = max(0, min(100, 2 * (ap["rssi"] + 100)))
        mq = re.search(r"Quality=(\d+)/(\d+)", line)
        if mq and ap["signal"] == 0:
            ap["signal"] = int(100 * int(mq.group(1)) / int(mq.group(2)))
        if "Encryption key:off" in line:
            ap["auth"] = "Abierta"
        elif "Encryption key:on" in line:
            ap["auth"] = "WPA/WPA2"
        if "WPA2" in line:
            ap["enc"] = "WPA2"
        elif "WPA" in line:
            ap["enc"] = "WPA"
    if ap:
        nets.append(_finish(ap))
    return nets


def _scan_linux():
    if plat.has_tool("nmcli"):
        nets = _scan_nmcli()
        if nets:
            return nets
    if plat.has_tool("iwlist"):
        nets = _scan_iwlist()
        if nets:
            return nets
    return []


# ----------------------------------------------------------------------
#  SIMULACION (sin adaptador / sin permisos)
# ----------------------------------------------------------------------
_SIM_NAMES = [
    ("INFINITUM_A4F2", "WPA2-Personal", "00E0FC"),
    ("TP-LINK_5G", "WPA2-Personal", "A42BB0"),
    ("IZZI-8830", "WPA2-Personal", "001DD0"),
    ("Totalplay-2.4G", "WPA3-Personal", "781DBA"),
    ("MEGACABLE_1122", "WPA2-Personal", "4C9EFF"),
    ("HP-Setup", "", "3C0754"),
    ("iPhone de Ana", "WPA2-Personal", "F0DBF8"),
    ("<oculta>", "WPA2-Personal", "8425DB"),
    ("CFE_Publico", "", "00146C"),
    ("NETGEAR_5G", "WPA2-Personal", "A040A0"),
    ("Xfinity", "", "1071F9"),
    ("ESP32-Sensor", "", "246F28"),
]


def _scan_sim(seed=None):
    import random
    rng = random.Random(seed)
    nets = []
    picked = rng.sample(_SIM_NAMES, k=rng.randint(6, len(_SIM_NAMES)))
    for name, auth, oui_pref in picked:
        ch = rng.choice([1, 6, 11, 36, 44, 149, 157])
        sig = rng.randint(18, 99)
        bssid = oui_pref.lower() + "".join(":%02x" % rng.randint(0, 255) for _ in range(3))
        bssid = ":".join(re.findall("..", oui_pref.lower())) + bssid[6:]
        nets.append(_finish({
            "ssid": name, "bssid": bssid, "signal": sig, "rssi": None,
            "channel": ch, "band": band_from_channel(ch),
            "auth": auth or "Abierta", "enc": "CCMP" if auth else "Ninguno",
            "radio": "802.11ac" if ch >= 36 else "802.11n",
        }))
    return nets


# ----------------------------------------------------------------------
#  API publica
# ----------------------------------------------------------------------
def scan():
    """
    Devuelve (mode, networks). mode in {"EN VIVO","SIMULACION"}.
    Elige el metodo segun el SO; si no obtiene nada, simula.
    """
    o = plat.os_name()
    nets = []
    if o == "windows":
        nets = _scan_windows()
    elif o == "linux":
        nets = _scan_linux()
    mode = "EN VIVO"
    if not nets:
        nets = _scan_sim()
        mode = "SIMULACION"
    nets.sort(key=lambda n: n["signal"], reverse=True)
    return mode, nets


# ----------------------------------------------------------------------
#  IPs: tu conexion + vecinos de la red (tabla ARP)
# ----------------------------------------------------------------------
_RE_IP = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b")
_RE_MAC = re.compile(r"\b([0-9A-Fa-f]{2}(?:[:-][0-9A-Fa-f]{2}){5})\b")


def local_info():
    """Tu IP local, la puerta de enlace (router) y el SSID conectado."""
    info = {"ip": None, "gateway": None, "ssid": None, "os": plat.os_name()}
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        info["ip"] = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    o = plat.os_name()
    if o == "windows":
        txt = _run(["ipconfig"], timeout=10)
        lines = txt.splitlines()
        for i, line in enumerate(lines):
            if re.search(r"(Puerta de enlace predeterminada|Default Gateway)", line, re.I):
                # la IPv4 puede venir en la misma linea o en la de abajo (Windows
                # a veces pone la IPv6 arriba y la IPv4 en una linea continuada)
                for cand in [line] + lines[i + 1:i + 3]:
                    mi = _RE_IP.search(cand)
                    if mi:
                        info["gateway"] = mi.group(1)
                        break
            if info["gateway"]:
                break
        it = _run(["netsh", "wlan", "show", "interfaces"], timeout=10)
        ms = re.search(r"^\s*SSID\s*:\s*(.+)$", it, re.MULTILINE | re.IGNORECASE)
        if ms:
            info["ssid"] = ms.group(1).strip()
    elif o == "linux":
        txt = _run(["ip", "route"], timeout=10)
        m = re.search(r"default via ([\d.]+)", txt)
        if m:
            info["gateway"] = m.group(1)
        it = _run(["nmcli", "-t", "-f", "ACTIVE,SSID", "dev", "wifi"], timeout=10)
        for line in it.splitlines():
            if line.split(":", 1)[0] in ("yes", "sí", "si"):
                info["ssid"] = line.split(":", 1)[1]
                break
    return info


def arp_neighbors():
    """
    Dispositivos vistos en tu red local con IP + MAC + fabricante, leyendo la
    tabla ARP (`arp -a`, y `ip neigh` en Linux). Son los equipos con los que tu
    maquina ha hablado (router, telefonos, TVs, IoT...). No es un escaneo
    intrusivo: solo lee lo que el sistema ya conoce.
    """
    hosts, seen = [], set()

    def _consume(txt):
        for line in txt.splitlines():
            mip, mmac = _RE_IP.search(line), _RE_MAC.search(line)
            if not (mip and mmac):
                continue
            ip = mip.group(1)
            mac = mmac.group(1).replace("-", ":").lower()
            if mac == "ff:ff:ff:ff:ff:ff" or ip.endswith(".255") \
               or ip.startswith(("224.", "239.", "255.")):
                continue
            key = ip + mac
            if key in seen:
                continue
            seen.add(key)
            hosts.append({"ip": ip, "mac": mac, "vendor": oui.vendor(mac)})

    _consume(_run(["arp", "-a"], timeout=10))
    if plat.os_name() == "linux" and not hosts:
        _consume(_run(["ip", "neigh"], timeout=10))
    hosts.sort(key=lambda h: tuple(int(x) for x in h["ip"].split(".")))
    return hosts
