#!/usr/bin/env bash
# ============================================================
#  radarWIFI PRO - setup para Linux (Kali / Parrot / Debian)
#  Instala las herramientas para desbloquear TODAS las capacidades:
#  modo monitor, deauth ligero y captura de handshakes.
# ============================================================
set -e

echo "==> radarWIFI PRO :: setup Linux"

if [ "$EUID" -ne 0 ]; then
  echo "   (aviso) para modo monitor/deauth tendras que correr la app con sudo."
fi

echo "==> Instalando herramientas del sistema (nmap, aircrack-ng, iw, wireshark)..."
if command -v apt >/dev/null 2>&1; then
  sudo apt update
  sudo apt install -y nmap aircrack-ng iw wireshark tshark net-tools python3 python3-pip
elif command -v pacman >/dev/null 2>&1; then
  sudo pacman -S --needed nmap aircrack-ng iw wireshark-cli net-tools python python-pip
else
  echo "   No reconozco tu gestor de paquetes. Instala manualmente: nmap aircrack-ng iw tshark"
fi

echo "==> Instalando dependencias Python opcionales (scapy)..."
pip3 install -r requirements.txt || python3 -m pip install scapy

echo ""
echo "==> Listo. Arranca con:"
echo "      sudo python3 server.py      # con root = todas las capacidades"
echo "      python3 server.py           # sin root = solo recon (radar + nmap)"
echo ""
echo "   Recuerda: un adaptador WiFi con soporte de MODO MONITOR es obligatorio"
echo "   para deauth/handshakes. Recomendados: Alfa AWUS036ACH/036NHA, TP-Link"
echo "   TL-WN722N v1, o cualquier chip Atheros AR9271 / Ralink RT3070 / MT7612U."
