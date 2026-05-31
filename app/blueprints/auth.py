"""Регистрация, вход, выход."""
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user

from ..extensions import db
from ..models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        login = request.form.get("login", "").strip()
        full_name = request.form.get("full_name", "").strip()
        password = request.form.get("password", "")
        password2 = request.form.get("password2", "")

        if not login or not password:
            flash("Логин и пароль обязательны.", "danger")
        elif password != password2:
            flash("Пароли не совпадают.", "danger")
        elif User.query.filter_by(login=login).first():
            flash("Пользователь с таким логином уже существует.", "danger")
        else:
            user = User(login=login, full_name=full_name, role="student")
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Регистрация прошла успешно!", "success")
            return redirect(url_for("main.index"))

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        login = request.form.get("login", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(login=login).first()

        if user and user.check_password(password):
            login_user(user)
            flash("Вы вошли в систему.", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("main.index"))
        flash("Неверный логин или пароль.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Вы вышли из системы.", "info")
    return redirect(url_for("main.index"))
