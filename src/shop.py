from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, send_file
)
from werkzeug.exceptions import abort
from src.auth import login_required
from src.db import get_db
import functools

bp = Blueprint('shop', __name__, url_prefix='/shop')

def shop_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        g.shopuser = get_db().execute(
            'SELECT * FROM shopuser WHERE userid = ?',
            (g.user['id'],)
        ).fetchone()
        if g.shopuser is None:
            flash("你尚未完善商店个人信息")
            return redirect(url_for('shop.adduserinfo'))
        return view(**kwargs)

    return wrapped_view

@bp.route('/')
def index():
    return render_template('shop/index.html')

@bp.route('/adduserinfo')
def adduserinfo():
    return render_template('shop/index.html')