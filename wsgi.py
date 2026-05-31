"""Точка входа для gunicorn на Render: gunicorn wsgi:app"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run()
