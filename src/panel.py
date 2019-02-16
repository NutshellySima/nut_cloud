from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

from src.auth import login_required
from src.db import get_db

bp=Blueprint('panel', __name__)

@bp.route('/')
def index():
    return render_template('panel/index.html')