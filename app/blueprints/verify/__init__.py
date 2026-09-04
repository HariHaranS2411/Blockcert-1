from flask import Blueprint

verify_bp = Blueprint('verify', __name__)

from app.blueprints.verify import routes  # noqa: E402, F401
