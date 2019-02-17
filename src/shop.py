from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, send_file
)
from werkzeug.exceptions import abort
from src.auth import login_required
from src.db import get_db
import functools
import os
import os, fnmatch

bp = Blueprint('shop', __name__, url_prefix='/shop')
basedir="../upload_files/anyone/shop"

def find(pattern, path):
    result = []
    for root, dirs, files in os.walk(path):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                result.append(os.path.join(root, name))
    return result

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

def shop_admin_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.shopuser['isadmin'] == False:
            flash("你不是管理员")
            return redirect(url_for('index'))
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
@shop_admin_required
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
    info=db.execute(
        'INSERT INTO goods (name, value, amount, type, isOnsale, description) VALUES (?, ?, ?, ?, ?, ?)',
        (name, value, amount, gtype, isOnsale, description,)
    )
    db.commit()
    return redirect(url_for('shop.addpic',id=info.lastrowid))

@bp.route('/addpic',methods=['POST','GET'])
@login_required
@shop_required
@shop_admin_required
def addpic():
    if request.method=='GET':
        return render_template('shop/addpic.html', id=request.values['id'])
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.referrer)
    files = request.files.getlist("file")
    for file in files:
        split_file_name = os.path.splitext(file.filename)
        path = str(request.form['id']) + split_file_name[1]
        path=os.path.join(basedir, path)
        file.save(path)
    return redirect(url_for('shop.index'))

@bp.route('/getpic/<int:id>')
def getpic(id):
    path=os.path.abspath(find(str(id)+'.*',basedir)[0])
    return send_file(path, conditional=True)