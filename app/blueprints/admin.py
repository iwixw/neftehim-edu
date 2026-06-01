"""Админ-панель: управление категориями и оборудованием каталога.

Доступ только для пользователей с ролью 'admin'.
"""
import re
from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from ..extensions import db
from ..models import (Category, Equipment, User, Bookmark, Term, Course, Lesson,
                      CourseQuestion, CourseAnswer, TestResult, LessonProgress)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(view):
    """Декоратор: пускает только администратора."""
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def _slugify(value):
    value = value.lower().strip()
    translit = {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
        "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
        "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
        "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "",
        "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya", " ": "-",
    }
    value = "".join(translit.get(ch, ch) for ch in value)
    value = re.sub(r"[^a-z0-9\-]", "", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "category"


@admin_bp.route("/")
@admin_required
def dashboard():
    # Админ-панель объединена с личным кабинетом
    return redirect(url_for("cabinet.index"))


@admin_bp.route("/results")
@admin_required
def results():
    """Результаты тестов учеников: общий журнал + лучшие баллы по ученикам."""
    course_filter = request.args.get("course", type=int)

    query = TestResult.query
    if course_filter:
        query = query.filter_by(course_id=course_filter)
    attempts = query.order_by(TestResult.taken_at.desc()).all()

    # сводка по ученикам: лучший балл по каждому курсу
    summary = {}  # user_id -> {user, best: {course_id: result}, lessons_done}
    for r in TestResult.query.all():
        s = summary.setdefault(r.user_id, {"user": r.user, "best": {}})
        cur = s["best"].get(r.course_id)
        if cur is None or r.score > cur.score:
            s["best"][r.course_id] = r

    stats = {
        "attempts": TestResult.query.count(),
        "passed": TestResult.query.filter_by(passed=True).count(),
        "students": db.session.query(TestResult.user_id).distinct().count(),
    }
    courses = Course.query.order_by(Course.position, Course.title).all()
    return render_template(
        "admin/results.html",
        attempts=attempts, summary=list(summary.values()),
        stats=stats, courses=courses, course_filter=course_filter,
    )


# --- Категории --------------------------------------------------------------
@admin_bp.route("/categories")
@admin_required
def category_list():
    categories = Category.query.order_by(Category.name).all()
    return render_template("admin/category_list.html", categories=categories)


@admin_bp.route("/categories/new", methods=["GET", "POST"])
@admin_bp.route("/categories/<int:cat_id>/edit", methods=["GET", "POST"])
@admin_required
def category_form(cat_id=None):
    category = Category.query.get_or_404(cat_id) if cat_id else None

    if request.method == "POST":
        f = request.form
        name = f.get("name", "").strip()
        if not name:
            flash("Укажите название категории.", "danger")
        else:
            if category is None:
                category = Category()
                db.session.add(category)
            category.name = name
            category.description = f.get("description", "").strip()
            category.icon = f.get("icon", "🛠️").strip() or "🛠️"
            slug = f.get("slug", "").strip() or _slugify(name)
            # гарантируем уникальность slug
            base, n = slug, 2
            existing = Category.query.filter(Category.slug == slug, Category.id != (category.id or 0)).first()
            while existing:
                slug = f"{base}-{n}"; n += 1
                existing = Category.query.filter(Category.slug == slug, Category.id != (category.id or 0)).first()
            category.slug = slug
            db.session.commit()
            flash("Категория сохранена.", "success")
            return redirect(url_for("admin.category_list"))

    return render_template("admin/category_form.html", category=category)


@admin_bp.route("/categories/<int:cat_id>/delete", methods=["POST"])
@admin_required
def category_delete(cat_id):
    category = Category.query.get_or_404(cat_id)
    db.session.delete(category)
    db.session.commit()
    flash("Категория удалена вместе с её оборудованием.", "info")
    return redirect(url_for("admin.category_list"))


# --- Оборудование -----------------------------------------------------------
@admin_bp.route("/equipment")
@admin_required
def equipment_list():
    items = Equipment.query.order_by(Equipment.title).all()
    return render_template("admin/equipment_list.html", items=items)


@admin_bp.route("/equipment/new", methods=["GET", "POST"])
@admin_bp.route("/equipment/<int:eq_id>/edit", methods=["GET", "POST"])
@admin_required
def equipment_form(eq_id=None):
    item = Equipment.query.get_or_404(eq_id) if eq_id else None
    categories = Category.query.order_by(Category.name).all()

    if request.method == "POST":
        f = request.form
        if item is None:
            item = Equipment()
            db.session.add(item)
        item.category_id = f.get("category_id", type=int)
        item.title = f.get("title", "").strip()
        item.marking = f.get("marking", "").strip()
        item.purpose = f.get("purpose", "").strip()
        item.operating_principle = f.get("operating_principle", "").strip()
        item.specifications = f.get("specifications", "").strip()
        item.application = f.get("application", "").strip()
        item.standards = f.get("standards", "").strip()
        item.safety_notes = f.get("safety_notes", "").strip()

        # Загрузка изображения
        upload = request.files.get("image")
        allowed = {"image/jpeg", "image/png", "image/webp", "image/gif"}
        if upload and upload.filename:
            if upload.mimetype not in allowed:
                flash("Изображение должно быть JPEG, PNG, WEBP или GIF.", "danger")
                return render_template("admin/equipment_form.html", item=item, categories=categories)
            item.image_data = upload.read()
            item.image_mime = upload.mimetype
        elif f.get("remove_image") == "1":
            item.image_data = None
            item.image_mime = None

        if not item.title or not item.category_id:
            flash("Заполните название и категорию.", "danger")
        else:
            db.session.commit()
            flash("Оборудование сохранено.", "success")
            return redirect(url_for("admin.equipment_list"))

    return render_template("admin/equipment_form.html", item=item, categories=categories)


@admin_bp.route("/equipment/<int:eq_id>/delete", methods=["POST"])
@admin_required
def equipment_delete(eq_id):
    item = Equipment.query.get_or_404(eq_id)
    db.session.delete(item)
    db.session.commit()
    flash("Оборудование удалено.", "info")
    return redirect(url_for("admin.equipment_list"))


# --- Глоссарий --------------------------------------------------------------
@admin_bp.route("/terms")
@admin_required
def term_list():
    terms = Term.query.order_by(Term.term).all()
    return render_template("admin/term_list.html", terms=terms)


@admin_bp.route("/terms/new", methods=["GET", "POST"])
@admin_bp.route("/terms/<int:term_id>/edit", methods=["GET", "POST"])
@admin_required
def term_form(term_id=None):
    term = Term.query.get_or_404(term_id) if term_id else None

    if request.method == "POST":
        name = request.form.get("term", "").strip()
        definition = request.form.get("definition", "").strip()
        if not name or not definition:
            flash("Заполните термин и определение.", "danger")
        else:
            dup = Term.query.filter(Term.term == name, Term.id != (term.id if term else 0)).first()
            if dup:
                flash("Такой термин уже есть.", "danger")
            else:
                if term is None:
                    term = Term()
                    db.session.add(term)
                term.term = name
                term.definition = definition
                db.session.commit()
                flash("Термин сохранён.", "success")
                return redirect(url_for("admin.term_list"))

    return render_template("admin/term_form.html", term=term)


@admin_bp.route("/terms/<int:term_id>/delete", methods=["POST"])
@admin_required
def term_delete(term_id):
    term = Term.query.get_or_404(term_id)
    db.session.delete(term)
    db.session.commit()
    flash("Термин удалён.", "info")
    return redirect(url_for("admin.term_list"))


# --- Курсы ------------------------------------------------------------------
@admin_bp.route("/courses")
@admin_required
def course_list():
    courses = Course.query.order_by(Course.position, Course.title).all()
    return render_template("admin/course_list.html", courses=courses)


@admin_bp.route("/courses/new", methods=["GET", "POST"])
@admin_bp.route("/courses/<int:course_id>/edit", methods=["GET", "POST"])
@admin_required
def course_form(course_id=None):
    course = Course.query.get_or_404(course_id) if course_id else None

    if request.method == "POST":
        f = request.form
        title = f.get("title", "").strip()
        if not title:
            flash("Укажите название курса.", "danger")
        else:
            if course is None:
                course = Course()
                db.session.add(course)
            course.title = title
            course.description = f.get("description", "").strip()
            course.icon = f.get("icon", "📘").strip() or "📘"
            course.level = f.get("level", "Базовый").strip() or "Базовый"
            course.position = f.get("position", type=int) or 0
            slug = f.get("slug", "").strip() or _slugify(title)
            base, n = slug, 2
            while Course.query.filter(Course.slug == slug, Course.id != (course.id or 0)).first():
                slug = f"{base}-{n}"; n += 1
            course.slug = slug
            db.session.commit()
            flash("Курс сохранён.", "success")
            return redirect(url_for("admin.course_detail", course_id=course.id))

    return render_template("admin/course_form.html", course=course)


@admin_bp.route("/courses/<int:course_id>")
@admin_required
def course_detail(course_id):
    course = Course.query.get_or_404(course_id)
    return render_template("admin/course_detail.html", course=course)


@admin_bp.route("/courses/<int:course_id>/delete", methods=["POST"])
@admin_required
def course_delete(course_id):
    course = Course.query.get_or_404(course_id)
    db.session.delete(course)
    db.session.commit()
    flash("Курс удалён.", "info")
    return redirect(url_for("admin.course_list"))


@admin_bp.route("/courses/<int:course_id>/lessons/new", methods=["GET", "POST"])
@admin_bp.route("/lessons/<int:lesson_id>/edit", methods=["GET", "POST"])
@admin_required
def lesson_form(course_id=None, lesson_id=None):
    lesson = Lesson.query.get_or_404(lesson_id) if lesson_id else None
    course = lesson.course if lesson else Course.query.get_or_404(course_id)

    if request.method == "POST":
        f = request.form
        title = f.get("title", "").strip()
        content = f.get("content", "").strip()
        if not title:
            flash("Укажите название урока.", "danger")
        else:
            if lesson is None:
                lesson = Lesson(course_id=course.id)
                db.session.add(lesson)
            lesson.title = title
            lesson.content = content
            lesson.position = f.get("position", type=int) or 0
            db.session.commit()
            flash("Урок сохранён.", "success")
            return redirect(url_for("admin.course_detail", course_id=course.id))

    return render_template("admin/lesson_form.html", course=course, lesson=lesson)


@admin_bp.route("/lessons/<int:lesson_id>/delete", methods=["POST"])
@admin_required
def lesson_delete(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    course_id = lesson.course_id
    db.session.delete(lesson)
    db.session.commit()
    flash("Урок удалён.", "info")
    return redirect(url_for("admin.course_detail", course_id=course_id))


# --- Вопросы итогового теста курса ------------------------------------------
@admin_bp.route("/courses/<int:course_id>/questions/new", methods=["GET", "POST"])
@admin_bp.route("/course-questions/<int:question_id>/edit", methods=["GET", "POST"])
@admin_required
def course_question_form(course_id=None, question_id=None):
    question = CourseQuestion.query.get_or_404(question_id) if question_id else None
    course = question.course if question else Course.query.get_or_404(course_id)

    if request.method == "POST":
        text = request.form.get("text", "").strip()
        options = [o.strip() for o in request.form.getlist("option") if o.strip()]
        correct_index = request.form.get("correct", type=int)

        if not text or len(options) < 2 or correct_index is None:
            flash("Нужен текст вопроса, минимум 2 варианта и отметка верного.", "danger")
        else:
            if question is None:
                question = CourseQuestion(course_id=course.id,
                                          position=len(course.questions) + 1)
                db.session.add(question)
            question.text = text
            for a in list(question.answers):
                db.session.delete(a)
            for i, opt in enumerate(options):
                db.session.add(CourseAnswer(
                    question=question, text=opt, is_correct=(i == correct_index)))
            db.session.commit()
            flash("Вопрос сохранён.", "success")
            return redirect(url_for("admin.course_detail", course_id=course.id))

    return render_template("admin/course_question_form.html", course=course, question=question)


@admin_bp.route("/course-questions/<int:question_id>/delete", methods=["POST"])
@admin_required
def course_question_delete(question_id):
    question = CourseQuestion.query.get_or_404(question_id)
    course_id = question.course_id
    db.session.delete(question)
    db.session.commit()
    flash("Вопрос удалён.", "info")
    return redirect(url_for("admin.course_detail", course_id=course_id))
