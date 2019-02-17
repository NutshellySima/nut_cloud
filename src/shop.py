from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, send_file
)
from werkzeug.exceptions import abort
from src.auth import login_required
from src.db import get_db
import functools
import os
import os, fnmatch
import markdown2

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
    db=get_db()
    goods=db.execute(
        'SELECT id, name, value FROM goods where isOnsale=1'
    ).fetchall()
    return render_template('shop/index.html', goods=goods)

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
    isOnsale=1 if request.form.get("isOnsale")=='on' else 0
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

@bp.route('/getpic/<int:idnum>')
def getpic(idnum):
    path=os.path.abspath(find(str(idnum)+'.*',basedir)[0])
    return send_file(path, conditional=True)

@bp.route('/detail/<int:idnum>')
def detail(idnum):
    db=get_db()
    good=db.execute(
        'SELECT * FROM goods WHERE id = ?',
        (idnum,)
    ).fetchone()
    html=markdown2.markdown(good['description'])
    return render_template('shop/detail.html',good=good,html=html)


@bp.route('/amendgood/<int:idnum>',methods=['POST','GET'])
@login_required
@shop_required
@shop_admin_required
def amendgood(idnum):
    if request.method=='GET':
        db=get_db()
        good=db.execute(
            'SELECT * FROM goods WHERE id = ?',
            (idnum,)
        ).fetchone()
        return render_template('shop/amendgood.html',good=good)
    name=request.form.get("name")
    value=request.form.get("value")
    amount=request.form.get("amount")
    gtype=request.form.get("type")
    isOnsale=1 if request.form.get("isOnsale")=='on' else 0
    description=request.form.get("description")
    db=get_db()
    db.execute(
        'UPDATE goods SET name = ?, value = ?, amount = ?, type = ?, isOnsale = ?, description = ?',
        (name, value, amount, gtype, isOnsale, description,)
    )
    db.commit()
    return redirect(url_for('shop.index'))