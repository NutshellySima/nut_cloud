from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, send_file
)
from werkzeug.exceptions import abort
from src.auth import login_required
from src.db import get_db

bp = Blueprint('shop', __name__, url_prefix='/shop')

@bp.route('/')
def index():
    return render_template('shop/index.html')