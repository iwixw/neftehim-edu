"""Главная страница, интерактивная схема резервуара, статические разделы."""
from flask import Blueprint, render_template

from ..models import Category, Equipment, Hotspot

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    categories = Category.query.order_by(Category.name).all()
    equipment_count = Equipment.query.count()
    return render_template(
        "index.html",
        categories=categories,
        equipment_count=equipment_count,
    )


@main_bp.route("/tank")
def tank():
    """Интерактивная схема резервуара РВС с горячими точками и выносками.

    Подписи-выноски раскладываются по левому/правому полю и равномерно
    разносятся по высоте, чтобы не накладывались друг на друга.
    """
    W, H = 800, 560
    hotspots = Hotspot.query.join(Equipment).all()

    points = []
    for i, h in enumerate(hotspots, start=1):
        points.append({
            "num": i, "h": h,
            "sx": round(h.x / 100 * W, 1),
            "sy": round(h.y / 100 * H, 1),
            "side": "left" if h.x < 50 else "right",
        })

    # Равномерные «слоты» подписей по вертикали для каждого поля
    top, bottom = 70, H - 60
    for side in ("left", "right"):
        group = sorted([p for p in points if p["side"] == side], key=lambda p: p["sy"])
        n = len(group)
        for j, p in enumerate(group):
            ly = top + (bottom - top) * (j / (n - 1) if n > 1 else 0.5)
            p["ly"] = round(ly, 1)
            if side == "left":
                p["line_x"] = -34
                p["text_x"] = -42
                p["anchor"] = "end"
            else:
                p["line_x"] = W + 34
                p["text_x"] = W + 42
                p["anchor"] = "start"

    return render_template("tank.html", points=points, W=W, H=H)
