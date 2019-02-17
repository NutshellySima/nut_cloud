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

@login_required
@bp.route('/adduserinfo',methods=['POST','GET'])
def adduserinfo():
    if request.method == 'GET':
        return render_template('shop/userinfo.html')
    isadmin=g.user['isadmin']
    address=request.form['address']
    postalcode=request.form['postalcode']
    phone=request.form['phone']
    email=request.form['email']
    db=get_db()
    db.execute(
        'INSERT INTO shopuser (userid, phone, email, address, postalcode, isadmin) VALUES (?, ?, ?, ?, ?, ?)',
        (g.user['id'],phone,email,address,postalcode,isadmin,)
    )
    db.commit()
    return redirect(url_for('shop.index'))

@bp.route('/addgood',methods=['POST','GET'])
@login_required
@shop_required
def addgood():
    if request.method=='GET':
        return render_template('shop/addgood.html')
    name=request.form.get("name")
    value=request.form.get("value")
    amount=request.form.get("amount")
    gtype=request.form.get("type")
    isOnsale=True if request.form.get("isOnSale") else False
    description=request.form.get("description")
    db=get_db()
    db.execute(
        'INSERT INTO goods (name, value, amount, type, isOnsale, description) VALUES (?, ?, ?, ?, ?, ?)',
        (name, value, amount, gtype, isOnsale, description,)
    )
    db.commit()
    return render_template('shop/addgood.html')