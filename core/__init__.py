# -*- coding: utf-8 -*-
"""
radarWIFI PRO - nucleo modular.

Modulos:
    platform_detect  -> detecta SO y capacidades (nmap, scapy, monitor mode...)
    oui              -> fabricante a partir del MAC (offline)
    scanner          -> escaneo WiFi cross-platform (netsh / nmcli / iwlist / scapy)
    nmap_integration -> wrapper de nmap (subprocess + parseo XML, sin deps)
    database         -> historial de escaneos en SQLite
    export           -> reportes CSV / JSON / HTML estilo Kali
    attacks          -> modulos activos SOLO Linux (monitor, deauth ligero, handshake)
    sensing          -> WiFi sensing estilo RuView (mock / ESP32-CSI real)
    terminal         -> ejecutor de comandos de recon con lista blanca
"""
__all__ = [
    "platform_detect",
    "oui",
    "scanner",
    "nmap_integration",
    "database",
    "export",
    "attacks",
    "sensing",
    "terminal",
]
