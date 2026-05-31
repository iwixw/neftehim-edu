

## Структура проекта
```
app/
  __init__.py        фабрика приложения, обработчики ошибок
  extensions.py      db, login_manager
  models.py          Category, Equipment, Hotspot, User, Bookmark
  blueprints/        main, auth, catalog, cabinet, admin
  templates/         Jinja2-шаблоны
  static/            css, js
config.py            конфигурация (SQLite/PostgreSQL)
seed.py              наполнение БД учебным контентом
wsgi.py              точка входа gunicorn
render.yaml          инфраструктура для Render
```
