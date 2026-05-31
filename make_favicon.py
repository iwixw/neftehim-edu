"""Генерация фавикона сайта (фирменный градиентный шестиугольник).

Запуск однократно: python make_favicon.py
Создаёт app/static/favicon.ico и app/static/apple-touch-icon.png
"""
import math
import os

from PIL import Image, ImageDraw

OUT_DIR = os.path.join("app", "static")
SIZE = 256  # рисуем крупно, потом уменьшаем

# Фирменный градиент: #3b5bff -> #7b3ff2
C1 = (59, 91, 255)
C2 = (123, 63, 242)


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def rounded_mask(size, radius):
    m = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return m


def hexagon_points(cx, cy, r):
    pts = []
    for i in range(6):
        ang = math.pi / 180 * (60 * i - 90)  # вершиной вверх
        pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    return pts


def build(size):
    # вертикальный градиент
    base = Image.new("RGB", (size, size), C1)
    px = base.load()
    for y in range(size):
        col = lerp(C1, C2, y / (size - 1))
        for x in range(size):
            px[x, y] = col

    # скругление углов
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    img.paste(base, (0, 0), rounded_mask(size, int(size * 0.22)))

    # белый шестиугольник
    d = ImageDraw.Draw(img)
    pts = hexagon_points(size / 2, size / 2, size * 0.30)
    d.polygon(pts, outline=(255, 255, 255, 255))
    # толстый контур
    lw = max(2, int(size * 0.06))
    pts_closed = pts + [pts[0]]
    d.line(pts_closed, fill=(255, 255, 255, 255), width=lw, joint="curve")
    return img


def main():
    big = build(SIZE)
    os.makedirs(OUT_DIR, exist_ok=True)
    ico_path = os.path.join(OUT_DIR, "favicon.ico")
    big.save(ico_path, sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    big.resize((180, 180), Image.LANCZOS).save(os.path.join(OUT_DIR, "apple-touch-icon.png"))
    print("Создано:", ico_path, "и apple-touch-icon.png")


if __name__ == "__main__":
    main()
