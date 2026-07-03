# -*- coding: utf-8 -*-
"""
nmap_integration - wrapper de nmap SIN dependencias (subprocess + XML stdlib).

nmap corre igual en Windows y en Linux, por eso es el corazon del recon
cross-platform. Aqui NO usamos python-nmap: llamamos al binario con salida
XML (-oX -) y parseamos con xml.etree. Cero pip.

Perfiles pensados para APRENDER (que es justo lo que quieres):
    ping    -> descubrir hosts vivos (rapido, no toca puertos)   -sn
    quick   -> top 100 puertos                                   -F -T4
    full    -> 1000 puertos + version de servicios               -sV -T4
    deep    -> version + deteccion de SO (necesita root/admin)   -sV -O -A
"""
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET

from . import platform_detect as plat

# rutas comunes de nmap en Windows (por si aun no esta en el PATH tras instalar)
_WIN_NMAP_PATHS = [
    r"C:\Program Files (x86)\Nmap\nmap.exe",
    r"C:\Program Files\Nmap\nmap.exe",
]


def _nmap_bin():
    """Ruta al binario de nmap: primero el PATH, luego rutas conocidas de Windows."""
    p = shutil.which("nmap")
    if p:
        return p
    for c in _WIN_NMAP_PATHS:
        if os.path.exists(c):
            return c
    return None

PROFILES = {
    "ping":  {"args": ["-sn"],                 "desc": "Descubrir hosts vivos (ARP/ping, sin puertos)"},
    "quick": {"args": ["-F", "-T4"],           "desc": "Top 100 puertos, rapido"},
    "full":  {"args": ["-sV", "-T4"],          "desc": "1000 puertos + version de servicios"},
    "deep":  {"args": ["-sV", "-O", "-A", "-T4"], "desc": "Version + SO + scripts (requiere root/admin)"},
}


def available() -> bool:
    return _nmap_bin() is not None


def _parse_xml(xml_text: str) -> list:
    hosts = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return hosts
    for h in root.findall("host"):
        state = h.find("status")
        if state is not None and state.get("state") != "up":
            continue
        addr, mac, vendor = None, None, None
        for a in h.findall("address"):
            t = a.get("addrtype")
            if t == "ipv4":
                addr = a.get("addr")
            elif t == "mac":
                mac = a.get("addr")
                vendor = a.get("vendor")
        hostname = None
        hn = h.find("hostnames/hostname")
        if hn is not None:
            hostname = hn.get("name")
        ports = []
        for p in h.findall("ports/port"):
            st = p.find("state")
            if st is None or st.get("state") != "open":
                continue
            svc = p.find("service")
            ports.append({
                "port": int(p.get("portid")),
                "proto": p.get("protocol"),
                "service": (svc.get("name") if svc is not None else "?"),
                "product": (svc.get("product") if svc is not None else "") or "",
                "version": (svc.get("version") if svc is not None else "") or "",
            })
        osmatch = None
        om = h.find("os/osmatch")
        if om is not None:
            osmatch = "{} ({}%)".format(om.get("name"), om.get("accuracy"))
        hosts.append({
            "ip": addr, "mac": mac, "vendor": vendor, "hostname": hostname,
            "os": osmatch, "ports": ports,
        })
    return hosts


def scan(target: str, profile: str = "quick", timeout: int = 300) -> dict:
    """
    Corre nmap contra `target` (IP, rango CIDR o dominio) con un perfil.
    Devuelve dict: {ok, error, cmd, profile, hosts:[...], raw_xml}
    """
    if not available():
        return {"ok": False, "error": "nmap no esta instalado. Windows: https://nmap.org/download "
                                       "· Linux: sudo apt install nmap", "hosts": []}
    if profile not in PROFILES:
        profile = "quick"
    if not target or any(c in target for c in [";", "|", "&", "`", "$", "\n"]):
        return {"ok": False, "error": "Objetivo invalido.", "hosts": []}

    prof = PROFILES[profile]
    needs_root = profile == "deep"
    if needs_root and plat.os_name() != "windows" and not plat.is_root():
        # sin root, -O falla; degradamos a full para no romper
        prof = PROFILES["full"]
        profile = "full (degradado: 'deep' necesita sudo)"

    cmd = [_nmap_bin()] + prof["args"] + ["-oX", "-", target]
    try:
        out = subprocess.run(cmd, capture_output=True, timeout=timeout)
        xml_text = out.stdout.decode("utf-8", errors="replace")
        hosts = _parse_xml(xml_text)
        return {"ok": True, "error": None, "cmd": " ".join(cmd),
                "profile": profile, "hosts": hosts, "raw_xml": xml_text}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "nmap tardo demasiado (timeout).",
                "cmd": " ".join(cmd), "hosts": []}
    except Exception as e:
        return {"ok": False, "error": str(e), "cmd": " ".join(cmd), "hosts": []}
