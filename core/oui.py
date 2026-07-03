# -*- coding: utf-8 -*-
"""
oui - fabricante a partir de la MAC (100% offline).

La IEEE publica ~35 000 prefijos OUI; meterlos todos seria pesado. Aqui hay
un mapa curado con los fabricantes mas comunes en redes caseras (sobre todo
las de ISPs mexicanos: Telmex/Infinitum, Izzi, Totalplay, Megacable) mas los
grandes de routers/telefonos. Se puede extender pegando lineas en data/oui.txt
con formato:  AABBCC=Nombre del fabricante

Uso:
    from core import oui
    oui.vendor("a4:2b:b0:11:22:33")  -> "TP-Link"
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
_EXTRA_FILE = os.path.join(HERE, "..", "data", "oui.txt")

# prefijo (3 primeros octetos, hex mayus sin separador) -> fabricante
_BUILTIN = {
    # --- Espressif (ESP32/ESP8266: el hardware de RuView / IoT) ---
    "246F28": "Espressif (ESP32)", "3C71BF": "Espressif (ESP32)",
    "A4CF12": "Espressif (ESP32)", "8CAAB5": "Espressif (ESP32)",
    "7C9EBD": "Espressif (ESP32)", "2462AB": "Espressif (ESP32)",
    # --- TP-Link ---
    "A42BB0": "TP-Link", "50C7BF": "TP-Link", "EC086B": "TP-Link",
    "B0BE76": "TP-Link", "1C61B4": "TP-Link", "60E327": "TP-Link",
    # --- Huawei (Infinitum/Totalplay suelen ser Huawei) ---
    "00E0FC": "Huawei", "48435A": "Huawei", "781DBA": "Huawei",
    "F83DFF": "Huawei", "247F3C": "Huawei", "E0247F": "Huawei",
    # --- ZTE (Telmex/Infinitum) ---
    "0015EB": "ZTE", "4CAC0A": "ZTE", "9CD24B": "ZTE", "D0608C": "ZTE",
    # --- Arris / Commscope (Izzi, cablemodems) ---
    "001DD0": "Arris", "0024A1": "Arris", "1071F9": "Arris",
    "4C9EFF": "Arris", "AC2205": "Arris",
    # --- Technicolor (Izzi/Totalplay) ---
    "001A2A": "Technicolor", "3872C0": "Technicolor", "F8E4FB": "Technicolor",
    "681590": "Technicolor",
    # --- Askey (Totalplay) ---
    "0018F5": "Askey", "F0F249": "Askey",
    # --- Netgear ---
    "00146C": "Netgear", "A040A0": "Netgear", "9C3DCF": "Netgear",
    "B07FB9": "Netgear",
    # --- Cisco / Linksys ---
    "00000C": "Cisco", "001121": "Cisco", "58BC27": "Cisco",
    "002369": "Linksys", "C0C1C0": "Linksys",
    # --- Ubiquiti ---
    "0418D6": "Ubiquiti", "24A43C": "Ubiquiti", "788A20": "Ubiquiti",
    "FCECDA": "Ubiquiti",
    # --- Xiaomi ---
    "286C07": "Xiaomi", "50EC50": "Xiaomi", "F8A45F": "Xiaomi",
    "643E8C": "Xiaomi",
    # --- Apple ---
    "3C0754": "Apple", "F0DBF8": "Apple", "A85C2C": "Apple",
    "DC2B2A": "Apple", "8863DF": "Apple", "ACBC32": "Apple",
    # --- Samsung ---
    "5CF6DC": "Samsung", "8425DB": "Samsung", "F409D8": "Samsung",
    "E8508B": "Samsung",
    # --- Intel (tarjetas WiFi de laptops) ---
    "001DE0": "Intel", "3C58C2": "Intel", "A0A8CD": "Intel",
    "8C1645": "Intel", "9C305B": "Intel",
    # --- Realtek / MediaTek (antenas USB baratas, muy comun en pentest) ---
    "00E04C": "Realtek", "52540": "Realtek",
    "0017A5": "Ralink/MediaTek", "00C0CA": "Alfa Network",
    # --- MAC aleatoria de telefono (privacidad) ---
    # se detecta por bit local, ver vendor()
}

_cache = None


def _load():
    global _cache
    if _cache is not None:
        return _cache
    table = dict(_BUILTIN)
    try:
        if os.path.exists(_EXTRA_FILE):
            with open(_EXTRA_FILE, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    pref, name = line.split("=", 1)
                    pref = pref.replace(":", "").replace("-", "").upper().strip()
                    if len(pref) >= 6:
                        table[pref[:6]] = name.strip()
    except Exception:
        pass
    _cache = table
    return table


def _is_locally_administered(mac: str) -> bool:
    """Segundo bit menos significativo del primer octeto = MAC aleatoria (privacidad)."""
    try:
        first = int(mac.replace(":", "").replace("-", "")[0:2], 16)
        return bool(first & 0b10)
    except Exception:
        return False


def vendor(mac: str) -> str:
    """Devuelve el fabricante o '?' (o 'MAC privada' si es aleatoria)."""
    if not mac:
        return "?"
    pref = mac.replace(":", "").replace("-", "").upper()[:6]
    table = _load()
    if pref in table:
        return table[pref]
    if _is_locally_administered(mac):
        return "MAC privada (aleatoria)"
    return "?"
