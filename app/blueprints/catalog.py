"""Каталог-учебник: список оборудования, фильтр по категориям, карточка изделия."""
from flask import Blueprint, render_template, request, Response, abort
from flask_login import current_user

from ..models import Category, Equipment, Bookmark

catalog_bp = Blueprint("catalog", __name__, url_prefix="/catalog")


@catalog_bp.route("/")
def index():
    categories = Category.query.order_by(Category.name).all()
    slug = request.args.get("category")
    query = request.args.get("q", "").strip()

    items_q = Equipment.query
    active_category = None
    if slug:
        active_category = Category.query.filter_by(slug=slug).first_or_404()
        items_q = items_q.filter_by(category_id=active_category.id)

    items = items_q.order_by(Equipment.title).all()

    # Регистронезависимый поиск на стороне Python — корректно работает
    # с кириллицей на любой СУБД (SQLite lower() не учитывает Unicode).
    if query:
        q = query.casefold()
        items = [
            it for it in items
            if q in (it.title or "").casefold() or q in (it.marking or "").casefold()
        ]
    return render_template(
        "catalog/index.html",
        categories=categories,
        items=items,
        active_category=active_category,
        query=query,
    )


@catalog_bp.route("/equipment/<int:eq_id>")
def equipment(eq_id):
    item = Equipment.query.get_or_404(eq_id)
    related = (
        Equipment.query
        .filter(Equipment.category_id == item.category_id, Equipment.id != item.id)
        .order_by(Equipment.title)
        .limit(4)
        .all()
    )
    bookmark = None
    if current_user.is_authenticated:
        bookmark = Bookmark.query.filter_by(
            user_id=current_user.id, equipment_id=item.id
        ).first()
    return render_template(
        "catalog/equipment.html", item=item, related=related, bookmark=bookmark
    )


@catalog_bp.route("/compare")
def compare():
    """Сравнение характеристик 2–3 изделий в таблице."""
    all_items = Equipment.query.order_by(Equipment.title).all()

    # выбранные id (из выпадающих списков), без пустых и дублей, максимум 3
    selected_ids, seen = [], set()
    for raw in request.args.getlist("ids"):
        if raw and raw.isdigit():
            i = int(raw)
            if i not in seen:
                seen.add(i)
                selected_ids.append(i)
    selected_ids = selected_ids[:3]

    by_id = {it.id: it for it in all_items}
    selected = [by_id[i] for i in selected_ids if i in by_id]

    # строки таблицы сравнения: (заголовок, имя атрибута)
    rows = [
        ("Категория", "category_name"),
        ("Марка", "marking"),
        ("Назначение", "purpose"),
        ("Принцип работы", "operating_principle"),
        ("Технические характеристики", "specifications"),
        ("Область применения", "application"),
        ("Требования безопасности", "safety_notes"),
        ("Нормативные документы", "standards"),
    ]
    return render_template(
        "catalog/compare.html",
        all_items=all_items, selected=selected, selected_ids=selected_ids, rows=rows,
    )


@catalog_bp.route("/equipment/<int:eq_id>/image")
def equipment_image(eq_id):
    """Отдаёт изображение изделия из БД."""
    item = Equipment.query.get_or_404(eq_id)
    if not item.has_image:
        abort(404)
    return Response(item.image_data, mimetype=item.image_mime or "image/jpeg")
