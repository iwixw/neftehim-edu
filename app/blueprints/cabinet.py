"""Личный кабинет ученика: закладки (избранное) и отметки «изучено».

Кнопки-переключатели на карточке оборудования ведут сюда.
"""
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user

from ..extensions import db
from ..models import Bookmark, Equipment, Category, User

cabinet_bp = Blueprint("cabinet", __name__, url_prefix="/cabinet")


def _get_or_create_bookmark(equipment_id):
    bm = Bookmark.query.filter_by(
        user_id=current_user.id, equipment_id=equipment_id
    ).first()
    if bm is None:
        bm = Bookmark(user_id=current_user.id, equipment_id=equipment_id)
        db.session.add(bm)
    return bm


@cabinet_bp.route("/")
@login_required
def index():
    favorites = [b for b in current_user.bookmarks if b.is_favorite]
    studied = [b for b in current_user.bookmarks if b.is_studied]
    total_equipment = Equipment.query.count()
    progress = round(len(studied) / total_equipment * 100) if total_equipment else 0

    # Для администратора — статистика и доступ к управлению каталогом
    admin_stats = None
    if current_user.is_admin:
        admin_stats = {
            "categories": Category.query.count(),
            "equipment": total_equipment,
            "users": User.query.count(),
            "bookmarks": Bookmark.query.count(),
        }

    return render_template(
        "cabinet/index.html",
        favorites=favorites, studied=studied,
        total_equipment=total_equipment, progress=progress,
        admin_stats=admin_stats,
    )


@cabinet_bp.route("/toggle/<int:eq_id>/<string:flag>", methods=["POST"])
@login_required
def toggle(eq_id, flag):
    """Переключить отметку 'favorite' или 'studied' для изделия."""
    Equipment.query.get_or_404(eq_id)
    if flag not in ("favorite", "studied"):
        flash("Неизвестное действие.", "danger")
        return redirect(request.referrer or url_for("catalog.index"))

    bm = _get_or_create_bookmark(eq_id)
    if flag == "favorite":
        bm.is_favorite = not bm.is_favorite
    else:
        bm.is_studied = not bm.is_studied

    is_favorite, is_studied = bm.is_favorite, bm.is_studied
    # если обе отметки сняты — убираем пустую запись
    if not is_favorite and not is_studied and bm.id is not None:
        db.session.delete(bm)
    db.session.commit()

    # AJAX-запрос (fetch) получает JSON, обычная форма — редирект (фолбэк без JS)
    wants_json = (
        request.headers.get("X-Requested-With") == "fetch"
        or "application/json" in request.headers.get("Accept", "")
    )
    if wants_json:
        return jsonify(ok=True, is_favorite=bool(is_favorite), is_studied=bool(is_studied))

    return redirect(request.referrer or url_for("catalog.equipment", eq_id=eq_id))
