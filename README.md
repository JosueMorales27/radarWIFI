# 📡 radarWIFI

**Radar de redes WiFi 100% local.** Escanea las redes a tu alrededor y las pinta en un
radar estilo hacker (verde fósforo, barrido tipo Matrix). **Nada sale de tu PC** — cero
telemetría, cero nube, cero servidores de terceros. Todo corre en tu máquina.

Inspirado en la idea de [RuView](https://github.com/ruvnet/ruview) (WiFi sensing), pero
en vez de necesitar placas ESP32 + CSI, usa el adaptador WiFi que ya tienes vía `netsh`.

![radar](radar.png)

## ✨ Qué hace

- **Escaneo real** de redes WiFi (SSID, BSSID, señal, canal, banda 2.4/5/6 GHz, seguridad).
- **Radar animado**: cada red es un *blip*; señal fuerte = más cerca del centro (tú).
- **Detecta redes abiertas** (sin cifrado) y las marca en rojo ⚠️.
- **Panel** con conteo de redes, abiertas, 2.4 GHz y 5 GHz, y lista clickeable.
- **Cámara opcional**: fondo de webcam en modo "AR" (se activa con un botón).
- **Ping sonar** opcional cuando el barrido ilumina una red.
- **Modo simulación** automático si no hay adaptador WiFi (para verlo funcionar igual).

## 🚀 Cómo usarlo

**Requisito:** Python 3 y Windows con adaptador WiFi.

1. Doble click en **`radarWIFI.bat`** (o crea el acceso directo con icono, ver abajo).
2. Se abre solo en el navegador en `http://127.0.0.1:8777`.
3. Cierra la ventana negra para apagarlo.

> Si no tienes WiFi (ej. desktop con puro ethernet), arranca en **modo SIMULACIÓN**.
> En cuanto conectes una antena WiFi USB, se vuelve **EN VIVO** solo.

### Acceso directo con icono hacker (opcional)

```powershell
python make_icon.py   # genera radar.ico
# luego crea un acceso directo a radarWIFI.bat con radar.ico como icono
```

## 🧩 Cómo funciona (arquitectura)

```
┌─────────────┐   netsh wlan    ┌──────────────┐   JSON /api/scan   ┌──────────────┐
│  Adaptador  │ ─────────────►  │  server.py   │ ─────────────────► │  index.html  │
│  WiFi (SO)  │  show networks  │ (http.server)│                    │ (radar canvas)│
└─────────────┘                 └──────────────┘                    └──────────────┘
      señales reales              parseo es/en                       animación + UI
```

- **Backend** (`server.py`): solo stdlib de Python (sin dependencias). Corre `netsh`,
  parsea la salida (funciona en Windows en español o inglés) y la sirve como JSON en
  `127.0.0.1` (solo localhost, no expuesto a la red).
- **Frontend** (`index.html`): un solo archivo, HTML + Canvas + JS puro. Radar, panel,
  cámara (getUserMedia) y sonido (WebAudio).
- **Icono** (`make_icon.py`): genera `radar.ico` con Pillow.

## 🔒 Privacidad

Este proyecto existe justamente para **no mandarle tus datos de WiFi a nadie**. El
servidor escucha solo en `127.0.0.1`, no hay llamadas a internet, y el código es corto
y legible para que lo verifiques tú mismo.

## 📜 Licencia

MIT — haz lo que quieras con él.
