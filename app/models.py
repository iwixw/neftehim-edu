"""Модели данных обучающей системы (каталог-учебник).

Связи:
    Category 1 — * Equipment        (категория содержит изделия)
    Equipment 1 — 1 Hotspot          (точка на схеме резервуара ведёт на изделие)
    User 1 — * Bookmark * — 1 Equipment  (закладки и отметки «изучено»)
"""
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from .extensions import db, login_manager


class Category(db.Model):
    """Категория оборудования (раздел каталога-учебника)."""
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text, default="")
    icon = db.Column(db.String(16), default="🛠️")

    equipment = db.relationship(
        "Equipment", back_populates="category",
        cascade="all, delete-orphan", order_by="Equipment.title"
    )

    def __repr__(self):
        return f"<Category {self.name}>"


class Equipment(db.Model):
    """Единица оборудования — основная сущность каталога."""
    __tablename__ = "equipment"

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)

    title = db.Column(db.String(160), nullable=False)
    marking = db.Column(db.String(80), default="")          # марка/обозначение, напр. КДМ-150
    purpose = db.Column(db.Text, default="")                # назначение
    operating_principle = db.Column(db.Text, default="")    # принцип работы
    specifications = db.Column(db.Text, default="")         # технические характеристики
    application = db.Column(db.Text, default="")            # область применения
    standards = db.Column(db.String(255), default="")       # ГОСТ / нормативные документы
    safety_notes = db.Column(db.Text, default="")           # требования безопасности

    # Изображение хранится в БД (надёжно на Render с эфемерным диском)
    image_data = db.Column(db.LargeBinary)
    image_mime = db.Column(db.String(64))

    category = db.relationship("Category", back_populates="equipment")
    hotspot = db.relationship(
        "Hotspot", back_populates="equipment",
        uselist=False, cascade="all, delete-orphan"
    )
    bookmarks = db.relationship(
        "Bookmark", back_populates="equipment", cascade="all, delete-orphan"
    )

    @property
    def has_image(self):
        return self.image_data is not None

    def __repr__(self):
        return f"<Equipment {self.title}>"


class Hotspot(db.Model):
    """Горячая точка на интерактивной схеме резервуара (координаты в % от размера SVG)."""
    __tablename__ = "hotspots"

    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey("equipment.id"), nullable=False, unique=True)
    label = db.Column(db.String(80), nullable=False)
    x = db.Column(db.Float, nullable=False)   # 0..100
    y = db.Column(db.Float, nullable=False)   # 0..100

    equipment = db.relationship("Equipment", back_populates="hotspot")


class User(UserMixin, db.Model):
    """Пользователь системы. role: 'student' или 'admin'."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(64), unique=True, nullable=False)
    full_name = db.Column(db.String(160), default="")
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(16), default="student")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bookmarks = db.relationship(
        "Bookmark", back_populates="user",
        cascade="all, delete-orphan", order_by="Bookmark.created_at.desc()"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == "admin"


class Bookmark(db.Model):
    """Связь «пользователь — изделие»: в избранном и/или изучено.

    Одна строка на пару (user, equipment) — хранит обе отметки сразу.
    """
    __tablename__ = "bookmarks"
    __table_args__ = (
        db.UniqueConstraint("user_id", "equipment_id", name="uq_user_equipment"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    equipment_id = db.Column(db.Integer, db.ForeignKey("equipment.id"), nullable=False)
    is_favorite = db.Column(db.Boolean, default=False)   # «в избранном»
    is_studied = db.Column(db.Boolean, default=False)    # «изучено»
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="bookmarks")
    equipment = db.relationship("Equipment", back_populates="bookmarks")


class Course(db.Model):
    """Обучающий курс — набор уроков по теме."""
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, default="")
    icon = db.Column(db.String(16), default="📘")
    level = db.Column(db.String(40), default="Базовый")
    position = db.Column(db.Integer, default=0)

    lessons = db.relationship(
        "Lesson", back_populates="course",
        cascade="all, delete-orphan", order_by="Lesson.position"
    )

    @property
    def lesson_count(self):
        return len(self.lessons)

    def __repr__(self):
        return f"<Course {self.title}>"


class Lesson(db.Model):
    """Урок курса (теоретический материал)."""
    __tablename__ = "lessons"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, default="")
    position = db.Column(db.Integer, default=0)

    course = db.relationship("Course", back_populates="lessons")
    progress = db.relationship(
        "LessonProgress", back_populates="lesson", cascade="all, delete-orphan"
    )


class LessonProgress(db.Model):
    """Отметка о прохождении урока пользователем."""
    __tablename__ = "lesson_progress"
    __table_args__ = (
        db.UniqueConstraint("user_id", "lesson_id", name="uq_user_lesson"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey("lessons.id"), nullable=False)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User")
    lesson = db.relationship("Lesson", back_populates="progress")


class CourseQuestion(db.Model):
    """Вопрос итогового теста курса."""
    __tablename__ = "course_questions"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    position = db.Column(db.Integer, default=0)

    course = db.relationship("Course", backref=db.backref(
        "questions", cascade="all, delete-orphan", order_by="CourseQuestion.position"))
    answers = db.relationship(
        "CourseAnswer", back_populates="question", cascade="all, delete-orphan")

    @property
    def correct_answer(self):
        return next((a for a in self.answers if a.is_correct), None)


class CourseAnswer(db.Model):
    """Вариант ответа на вопрос теста."""
    __tablename__ = "course_answers"

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("course_questions.id"), nullable=False)
    text = db.Column(db.String(400), nullable=False)
    is_correct = db.Column(db.Boolean, default=False)

    question = db.relationship("CourseQuestion", back_populates="answers")


class TestResult(db.Model):
    """Результат прохождения итогового теста курса."""
    __tablename__ = "test_results"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    correct = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Integer, nullable=False)
    passed = db.Column(db.Boolean, default=False)
    taken_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User")
    course = db.relationship("Course")


class Term(db.Model):
    """Термин глоссария отраслевых понятий."""
    __tablename__ = "terms"

    id = db.Column(db.Integer, primary_key=True)
    term = db.Column(db.String(160), unique=True, nullable=False)
    definition = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f"<Term {self.term}>"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
