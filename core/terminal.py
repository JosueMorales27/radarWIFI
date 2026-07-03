# -*- coding: utf-8 -*-
"""
terminal - ejecutor de comandos de recon con LISTA BLANCA.

La terminal integrada de la UI manda comandos aqui. Para que sea segura y a la
vez util para APRENDER, solo se permiten herramientas de red/recon conocidas
(nmap, ping, traceroute, arp, ip/ipconfig, nslookup/dig, iw, nmcli, tshark...).
Nada de rm, del, format, shutdown, etc. Sin shell=True: no hay inyeccion.
"""
import shlex
import subprocess

from . import platform_detect as plat

# comandos permitidos (por SO). La clave es el primer token.
_COMMON = {
    "nmap", "ping", "nslookup", "arp", "netstat", "tracert", "traceroute",
    "route", "whois", "curl", "host", "dig", "tshark", "dumpcap",
}
_WIN = {"ipconfig", "netsh", "pathping", "getmac"}
_LINUX = {"ip", "ifconfig", "iwconfig", "iw", "nmcli", "iwlist", "airmon-ng",
          "airodump-ng", "cat", "ls"}

# argumentos peligrosos que bloqueamos aunque el binario sea permitido
_BLOCK_TOKENS = {";", "|", "&", "&&", "||", ">", ">>", "<", "`", "$(", "rm", "del"}


def allowed_commands() -> list:
    o = plat.os_name()
    extra = _WIN if o == "windows" else (_LINUX if o == "linux" else set())
    return sorted(_COMMON | extra)


def run(command: str, timeout: int = 60) -> dict:
    """Corre un comando de la lista blanca. Devuelve {ok, output, error, cmd}."""
    command = (command or "").strip()
    if not command:
        return {"ok": False, "error": "Comando vacio."}

    # Windows: netsh usa comillas raras; usar split simple. Linux: shlex.
    try:
        parts = shlex.split(command, posix=(plat.os_name() != "windows"))
    except ValueError as e:
        return {"ok": False, "error": "No pude parsear el comando: {}".format(e)}
    if not parts:
        return {"ok": False, "error": "Comando vacio."}

    # bloquear encadenado / redireccion / borrado
    for tok in parts:
        if tok in _BLOCK_TOKENS or any(b in tok for b in (";", "|", "`", "$(", "&")):
            return {"ok": False, "error": "Caracter/operador no permitido: '{}'. "
                                          "La terminal solo corre UN comando de recon.".format(tok)}

    binary = parts[0].lower()
    # en Windows algunos vienen con .exe
    binary = binary[:-4] if binary.endswith(".exe") else binary
    if binary not in allowed_commands():
        return {"ok": False,
                "error": "'{}' no esta en la lista blanca. Permitidos: {}".format(
                    binary, ", ".join(allowed_commands()))}

    try:
        out = subprocess.run(parts, capture_output=True, shell=False, timeout=timeout)
        text = out.stdout.decode("utf-8", "replace") + out.stderr.decode("utf-8", "replace")
        return {"ok": True, "cmd": command, "output": text.strip() or "(sin salida)"}
    except FileNotFoundError:
        return {"ok": False, "error": "'{}' no esta instalado en este equipo.".format(binary)}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "El comando tardo demasiado (timeout {}s).".format(timeout)}
    except Exception as e:
        return {"ok": False, "error": str(e)}
