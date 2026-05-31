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
