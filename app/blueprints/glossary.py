"""Глоссарий отраслевых терминов (публичная страница с поиском)."""
from flask import Blueprint, render_template, request

from ..models import Term

glossary_bp = Blueprint("glossary", __name__, url_prefix="/glossary")


@glossary_bp.route("/")
def index():
    query = request.args.get("q", "").strip()
    terms = Term.query.order_by(Term.term).all()
    if query:
        q = query.casefold()
        terms = [
            t for t in terms
            if q in t.term.casefold() or q in t.definition.casefold()
        ]
    return render_template("glossary/index.html", terms=terms, query=query)
