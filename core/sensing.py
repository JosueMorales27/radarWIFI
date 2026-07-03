# -*- coding: utf-8 -*-
"""
sensing - WiFi sensing estilo RuView (ver personas SIN camara, usando como el
cuerpo perturba la senal WiFi: presencia, esqueleto 17 puntos, pulso,
respiracion y caidas).

MODO SIMULADO por defecto. El sensing REAL a traves de paredes necesita un
radio que exponga el CSI (Channel State Information). Ni tu router normal ni
netsh lo dan. Caminos reales para activarlo:
    - 2x ESP32-CSI (lo mas barato y fiel a RuView)  <-- recomendado
    - Nexmon CSI en Raspberry Pi 3B+/4/Zero 2 W
    - Intel 5300 + Linux CSI Tool / Atheros CSI Tool

Cuando conectes ese hardware, implementa read_csi_frame() para que devuelva
el mismo dict que sensing_frame() y listo: toda la UI sigue igual.
"""
import math
import time

# 17 keypoints estilo COCO (cabeza -> pies) en coords normalizadas [-1..1]
_POSE_BASE = [
    (0.00, -0.90),                       # 0 nariz
    (-0.04, -0.94), (0.04, -0.94),       # 1,2 ojos
    (-0.08, -0.92), (0.08, -0.92),       # 3,4 orejas
    (-0.18, -0.62), (0.18, -0.62),       # 5,6 hombros
    (-0.26, -0.30), (0.26, -0.30),       # 7,8 codos
    (-0.30, 0.02), (0.30, 0.02),         # 9,10 munecas
    (-0.12, -0.02), (0.12, -0.02),       # 11,12 caderas
    (-0.14, 0.44), (0.14, 0.44),         # 13,14 rodillas
    (-0.15, 0.88), (0.15, 0.88),         # 15,16 tobillos
]
_ACTIVITIES = ["de pie", "caminando", "sentado", "quieto"]


def has_csi_hardware() -> bool:
    """Hoy no hay soporte de CSI. Cambia esto cuando conectes las ESP32."""
    return False


def read_csi_frame():
    """
    STUB para hardware real (ESP32-CSI / Nexmon / Intel 5300).
    Debe devolver el MISMO dict que sensing_frame(). No implementado aun.
    """
    raise NotImplementedError("Conecta hardware CSI e implementa read_csi_frame().")


def sensing_frame():
    """Frame coherente en el tiempo. Real si hay hardware; si no, simulado."""
    if has_csi_hardware():
        try:
            return read_csi_frame()
        except Exception:
            pass  # cae a simulacion si el hardware falla

    t = time.time()
    n = 1 + int((math.sin(t * 0.07) + 1))  # 1..2 personas, cambia lento
    persons = []
    for i in range(n):
        ph = i * 2.3
        px = 0.5 + 0.28 * math.sin(t * 0.15 + ph)
        py = 0.5 + 0.22 * math.cos(t * 0.11 + ph * 1.7)
        moving = abs(math.sin(t * 0.15 + ph)) > 0.35
        act = "caminando" if moving else _ACTIVITIES[(i + int(t * 0.05)) % len(_ACTIVITIES)]
        breathing = round(15 + 3 * math.sin(t * 0.9 + ph), 1)
        heart = round(74 + 10 * math.sin(t * 0.5 + ph) + 2 * math.sin(t * 3 + ph), 0)
        sway = 0.03 * math.sin(t * 1.3 + ph)
        breathe = 0.015 * math.sin(t * (breathing / 60.0) * 2 * math.pi)
        kp = []
        for (kx, ky) in _POSE_BASE:
            jitter = 0.01 * math.sin(t * 2 + kx * 7 + ph)
            kp.append([round(kx + sway + jitter, 3), round(ky - breathe, 3)])
        persons.append({
            "id": i + 1, "x": round(px, 3), "y": round(py, 3),
            "activity": act, "moving": moving,
            "heart_rate": int(heart), "breathing_rate": breathing,
            "keypoints": kp,
            "confidence": round(0.72 + 0.2 * abs(math.sin(t + ph)), 2),
        })
    fall = (int(t) % 90) < 2 and n > 0
    motion = int(min(100, sum(60 if p["moving"] else 15 for p in persons)))
    return {
        "mode": "EN VIVO" if has_csi_hardware() else "SIMULADO",
        "hardware": has_csi_hardware(),
        "presence": n > 0, "person_count": n, "motion_level": motion,
        "fall_detected": bool(fall), "persons": persons,
    }
