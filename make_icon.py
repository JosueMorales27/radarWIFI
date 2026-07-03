# -*- coding: utf-8 -*-
"""Genera radar.ico: radar hacker (verde fosforo sobre negro, barrido + blips)."""
from PIL import Image, ImageDraw
import math, os

HERE = os.path.dirname(os.path.abspath(__file__))
GRN = (0, 255, 95)
DIM = (10, 125, 58)


def render(size):
    S = 256  # dibujamos grande y reducimos (antialias)
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = S / 2
    R = S * 0.46

    # disco negro
    d.ellipse([c - R, c - R, c + R, c + R], fill=(2, 10, 5, 255),
              outline=GRN + (255,), width=6)
    # anillos
    for i in (1, 2, 3):
        r = R * i / 3
        d.ellipse([c - r, c - r, c + r, c + r], outline=DIM + (200,), width=3)
    # cruz
    d.line([c - R, c, c + R, c], fill=DIM + (200,), width=3)
    d.line([c, c - R, c, c + R], fill=DIM + (200,), width=3)

    # cono de barrido (verde translucido)
    sweep = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sweep)
    sd.pieslice([c - R, c - R, c + R, c + R], -60, -18, fill=GRN + (90,))
    img = Image.alpha_composite(img, sweep)
    d = ImageDraw.Draw(img)
    # linea del barrido
    ang = math.radians(-18)
    d.line([c, c, c + math.cos(ang) * R, c + math.sin(ang) * R], fill=GRN + (255,), width=5)

    # blips
    for (bx, by, br) in [(0.62, 0.40, 10), (0.38, 0.62, 8), (0.68, 0.66, 7), (0.30, 0.35, 6)]:
        px, py = bx * S, by * S
        d.ellipse([px - br, py - br, px + br, py + br], fill=GRN + (255,))
    # centro (tu)
    d.ellipse([c - 7, c - 7, c + 7, c + 7], fill=(223, 255, 233, 255))

    return img.resize((size, size), Image.LANCZOS)


def main():
    sizes = [16, 24, 32, 48, 64, 128, 256]
    imgs = [render(s) for s in sizes]
    out = os.path.join(HERE, "radar.ico")
    imgs[0].save(out, format="ICO", sizes=[(s, s) for s in sizes],
                 append_images=imgs[1:])
    # tambien un PNG por si acaso
    render(256).save(os.path.join(HERE, "radar.png"))
    print("Icono generado:", out)


if __name__ == "__main__":
    main()
