from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

from nut_cloud.auth import login_required
from nut_cloud.db import get_db

bp=Blueprint('panel', __name__)

@bp.route('/')
def index():
    return render_template('panel/index.html')