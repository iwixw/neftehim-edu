"""Обучающие курсы: список, страница курса, урок, отметка о прохождении."""
from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user

from ..extensions import db
from ..models import Course, Lesson, LessonProgress, CourseQuestion, TestResult

courses_bp = Blueprint("courses", __name__, url_prefix="/courses")

PASS_SCORE = 60  # порог сдачи итогового теста, %


def _best_result(course_id):
    if not current_user.is_authenticated:
        return None
    results = TestResult.query.filter_by(
        user_id=current_user.id, course_id=course_id).all()
    return max(results, key=lambda r: r.score) if results else None


def _completed_lesson_ids():
    """Множество id уроков, пройденных текущим пользователем."""
    if not current_user.is_authenticated:
        return set()
    rows = LessonProgress.query.filter_by(user_id=current_user.id).all()
    return {r.lesson_id for r in rows}


def _course_progress(course, done_ids):
    total = course.lesson_count
    done = sum(1 for l in course.lessons if l.id in done_ids)
    percent = round(done / total * 100) if total else 0
    return done, total, percent


@courses_bp.route("/")
def index():
    courses = Course.query.order_by(Course.position, Course.title).all()
    done_ids = _completed_lesson_ids()
    cards = []
    for c in courses:
        done, total, percent = _course_progress(c, done_ids)
        cards.append({"course": c, "done": done, "total": total, "percent": percent})
    return render_template("courses/index.html", cards=cards)


@courses_bp.route("/<slug>")
def detail(slug):
    course = Course.query.filter_by(slug=slug).first_or_404()
    done_ids = _completed_lesson_ids()
    done, total, percent = _course_progress(course, done_ids)
    return render_template(
        "courses/detail.html",
        course=course, done_ids=done_ids,
        done=done, total=total, percent=percent,
        has_test=len(course.questions) > 0,
        best_result=_best_result(course.id),
    )


@courses_bp.route("/<slug>/lesson/<int:lesson_id>")
def lesson(slug, lesson_id):
    course = Course.query.filter_by(slug=slug).first_or_404()
    lesson = Lesson.query.get_or_404(lesson_id)
    if lesson.course_id != course.id:
        abort(404)

    lessons = course.lessons
    idx = next((i for i, l in enumerate(lessons) if l.id == lesson.id), 0)
    prev_lesson = lessons[idx - 1] if idx > 0 else None
    next_lesson = lessons[idx + 1] if idx < len(lessons) - 1 else None

    done_ids = _completed_lesson_ids()
    return render_template(
        "courses/lesson.html",
        course=course, lesson=lesson, number=idx + 1,
        prev_lesson=prev_lesson, next_lesson=next_lesson,
        is_done=lesson.id in done_ids,
    )


@courses_bp.route("/<slug>/lesson/<int:lesson_id>/complete", methods=["POST"])
@login_required
def complete(slug, lesson_id):
    course = Course.query.filter_by(slug=slug).first_or_404()
    lesson = Lesson.query.get_or_404(lesson_id)
    if lesson.course_id != course.id:
        abort(404)

    row = LessonProgress.query.filter_by(
        user_id=current_user.id, lesson_id=lesson.id
    ).first()
    if row:
        db.session.delete(row)  # повторное нажатие снимает отметку
        flash("Отметка о прохождении снята.", "info")
    else:
        db.session.add(LessonProgress(user_id=current_user.id, lesson_id=lesson.id))
        flash("Урок отмечен как пройденный!", "success")
    db.session.commit()

    # перейти к следующему уроку, если он есть
    lessons = course.lessons
    idx = next((i for i, l in enumerate(lessons) if l.id == lesson.id), 0)
    if not row and idx < len(lessons) - 1:
        return redirect(url_for("courses.lesson", slug=course.slug, lesson_id=lessons[idx + 1].id))
    return redirect(url_for("courses.lesson", slug=course.slug, lesson_id=lesson.id))


@courses_bp.route("/<slug>/test", methods=["GET", "POST"])
@login_required
def test(slug):
    course = Course.query.filter_by(slug=slug).first_or_404()
    questions = course.questions
    if not questions:
        flash("У этого курса пока нет итогового теста.", "warning")
        return redirect(url_for("courses.detail", slug=course.slug))

    if request.method == "POST":
        correct = 0
        review = []
        for q in questions:
            chosen_id = request.form.get(f"q{q.id}", type=int)
            right = q.correct_answer
            is_right = right is not None and chosen_id == right.id
            if is_right:
                correct += 1
            review.append({
                "question": q, "chosen_id": chosen_id,
                "correct_id": right.id if right else None, "is_right": is_right,
            })

        total = len(questions)
        score = round(correct / total * 100) if total else 0
        passed = score >= PASS_SCORE

        result = TestResult(
            user_id=current_user.id, course_id=course.id,
            score=score, correct=correct, total=total, passed=passed,
        )
        db.session.add(result)
        db.session.commit()

        return render_template(
            "courses/test_result.html",
            course=course, result=result, review=review, pass_score=PASS_SCORE,
        )

    return render_template("courses/test.html", course=course, questions=questions)
