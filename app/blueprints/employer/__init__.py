from flask import Blueprint

employer_bp = Blueprint('employer', __name__, url_prefix='/employer')

from app.blueprints.employer import routes  # noqa: E402, F401
