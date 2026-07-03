# -*- coding: utf-8 -*-
"""
platform_detect - que sistema operativo es y que puede hacer esta maquina.

La app es la misma en todos lados; lo que cambia son las CAPACIDADES.
En Windows tienes recon (netsh + nmap). En Linux, ademas, se desbloquean
modo monitor, deauth y captura de handshakes (si tienes las herramientas).
"""
import os
import sys
import shutil
import platform

_WIN_NMAP_PATHS = [
    r"C:\Program Files (x86)\Nmap\nmap.exe",
    r"C:\Program Files\Nmap\nmap.exe",
]


def has_nmap() -> bool:
    """nmap en el PATH o en su ruta de instalacion tipica de Windows."""
    if shutil.which("nmap"):
        return True
    return any(os.path.exists(p) for p in _WIN_NMAP_PATHS)


def os_name() -> str:
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform.startswith("linux"):
        return "linux"
    if sys.platform == "darwin":
        return "macos"
    return "unknown"


def has_tool(name: str) -> bool:
    """True si el binario existe en el PATH."""
    return shutil.which(name) is not None


def _has_scapy() -> bool:
    try:
        import scapy  # noqa: F401
        return True
    except Exception:
        return False


def is_root() -> bool:
    try:
        return hasattr(__import__("os"), "geteuid") and __import__("os").geteuid() == 0
    except Exception:
        return False


def capabilities() -> dict:
    """
    Devuelve un dict con todo lo que la UI necesita para prender/apagar botones.
    Nunca lanza excepcion: si algo falla, esa capacidad queda en False.
    """
    o = os_name()
    caps = {
        "os": o,
        "os_pretty": _safe(platform.platform),
        "machine": _safe(platform.machine),
        "python": platform.python_version(),
        "root": is_root(),
        # recon (cross-platform)
        "wifi_scan": True,           # siempre: netsh / nmcli / iwlist / scapy / sim
        "nmap": has_nmap(),
        "scapy": _has_scapy(),
        "wireshark_cli": has_tool("tshark") or has_tool("dumpcap"),
        # activos (por defecto apagados; solo Linux los enciende)
        "monitor_mode": False,
        "deauth": False,
        "handshake": False,
    }

    if o == "windows":
        caps["netsh"] = has_tool("netsh")
    elif o == "linux":
        caps["iw"] = has_tool("iw")
        caps["nmcli"] = has_tool("nmcli")
        caps["iwlist"] = has_tool("iwlist")
        caps["airmon"] = has_tool("airmon-ng")
        caps["airodump"] = has_tool("airodump-ng")
        caps["aireplay"] = has_tool("aireplay-ng")
        caps["monitor_mode"] = caps["iw"] or caps["airmon"]
        caps["deauth"] = caps["scapy"] or caps["aireplay"]
        caps["handshake"] = caps["airodump"]

    return caps


def _safe(fn):
    try:
        return fn()
    except Exception:
        return "?"


def why_disabled(cap: str) -> str:
    """Mensaje humano de por que una capacidad activa esta apagada."""
    o = os_name()
    if o != "linux":
        return ("Los ataques activos (deauth / handshake / modo monitor) requieren "
                "Linux (Kali/Parrot) + un adaptador WiFi compatible con modo monitor. "
                "En {} solo hay recon pasivo y nmap.".format(o))
    return ("Falta la herramienta necesaria. Instala aircrack-ng e iw:\n"
            "  sudo apt install aircrack-ng iw   (o corre setup.sh)")
