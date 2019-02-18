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

def pre_shop(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user:
            g.shopuser = get_db().execute(
                'SELECT * FROM shopuser WHERE userid = ?',
                (g.user['id'],)
            ).fetchone()
        else:
            g.shopuser=None
        return view(**kwargs)

    return wrapped_view

def shop_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        g.shopuser = get_db().execute(
            'SELECT * FROM shopuser WHERE userid = ?',
            (g.user['id'],)
        ).fetchone()
        if g.shopuser is None:
            flash("你尚未完善商店个人信息",category="error")
            return redirect(url_for('shop.adduserinfo'))
        return view(**kwargs)

    return wrapped_view

def shop_admin_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.shopuser['isadmin'] == False:
            flash("你不是管理员",category="error")
            return redirect(url_for('index'))
        return view(**kwargs)

    return wrapped_view

@bp.route('/')
@pre_shop
def index():
    db=get_db()
    goods=None
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
    description=request.form.get("description")
    db=get_db()
    info=db.execute(
        'INSERT INTO goods (name, value, amount, type, isOnsale, description) VALUES (?, ?, ?, ?, ?, ?)',
        (name, value, amount, gtype, 1, description,)
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
        flash('No file part',category="error")
        return redirect(request.referrer)
    files = request.files.getlist("file")
    for file in files:
        split_file_name = os.path.splitext(file.filename)
        path = str(request.form['id']) + split_file_name[1]
        path=os.path.join(basedir, path)
        file.save(path)
    return redirect(url_for('shop.index'))

@bp.route('/getpic/<int:idnum>')
@pre_shop
def getpic(idnum):
    path=os.path.abspath(find(str(idnum)+'.*',basedir)[0])
    return send_file(path, conditional=True)

@bp.route('/detail/<int:idnum>')
@pre_shop
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
        'UPDATE goods SET name = ?, value = ?, amount = ?, type = ?, isOnsale = ?, description = ? WHERE id = ?',
        (name, value, amount, gtype, isOnsale, description,idnum,)
    )
    db.commit()
    return redirect(url_for('shop.index'))

@bp.route('/deletegood/<int:idnum>',methods=['POST'])
@login_required
@shop_required
@shop_admin_required
def deletegood(idnum):
    db=get_db()
    db.execute(
        'UPDATE goods SET isOnSale=0 WHERE id = ?',
        (idnum,)
    )
    db.commit()
    return redirect(request.referrer)

@bp.route('/changeuserinfo',methods=['GET','POST'])
@login_required
@shop_required
def changeuserinfo():
    if request.method == 'GET':
        return render_template('shop/userinfo.html',i=g.shopuser)
    isadmin=g.user['isadmin']
    address=request.form['address']
    postalcode=request.form['postalcode']
    phone=request.form['phone']
    email=request.form['email']
    db=get_db()
    db.execute(
        'UPDATE shopuser SET phone = ?, email = ?, address = ?, postalcode = ?, isadmin = ? WHERE userid = ?',
        (phone,email,address,postalcode,isadmin,g.user['id'],)
    )
    db.commit()
    return redirect(url_for('shop.index'))

@bp.route('/search',methods=['GET'])
@pre_shop
def search():
    search_name=request.values.get('search_name')
    db=get_db()
    goods=None
    if g.shopuser and g.shopuser['isadmin']==1:
        goods=db.execute(
            'SELECT id, name, value FROM goods WHERE name LIKE ?',
            ("%"+search_name+"%",)
        ).fetchall()
    else:
        goods=db.execute(
            'SELECT id, name, value FROM goods where isOnsale=1 AND name LIKE ?',
            ("%"+search_name+"%",)
        ).fetchall()
    return render_template('shop/index.html', goods=goods)

@bp.route('/buy/<int:idnum>',methods=['POST'])
@login_required
@shop_required
def buy(idnum):
    db=get_db()
    info=db.execute(
        'SELECT amount FROM cart WHERE goodid = ? AND ticketid IS NULL',
        (idnum,)
    ).fetchone()
    if info is None:
        db.execute(
            'INSERT INTO cart (goodid, amount, userid) VALUES (?, ?, ?)',
            (idnum, 1, g.user['id'],)
        )
    else:
        db.execute(
            'UPDATE cart SET amount = ? WHERE goodid = ? AND ticketid IS NULL',
            (info['amount']+1,idnum,)
        )
    db.commit()
    flash("商品已成功加入购物车")
    return redirect(request.referrer)

@bp.route('/minusone/<int:idnum>',methods=['POST'])
@login_required
@shop_required
def minusone(idnum):
    db=get_db()
    info=db.execute(
        'SELECT amount FROM cart WHERE goodid = ? AND ticketid IS NULL',
        (idnum,)
    ).fetchone()
    if info is None:
        flash("非法-1操作",category="error")
        return redirect(request.referrer)
    amount=info['amount']-1
    if amount == 0:
        db.execute(
            'DELETE FROM cart WHERE goodid = ? AND ticketid IS NULL',
            (idnum,)
        )
    else:
        db.execute(
            'UPDATE cart SET amount = ? WHERE goodid = ? AND ticketid IS NULL',
            (amount,idnum,)
        )
    db.commit()
    flash("商品已成功-1")
    return redirect(request.referrer)

@bp.route('/delete/<int:idnum>',methods=['POST'])
@login_required
@shop_required
def delete(idnum):
    db=get_db()
    info=db.execute(
        'SELECT amount FROM cart WHERE goodid = ? AND ticketid IS NULL',
        (idnum,)
    ).fetchone()
    if info is None:
        flash("非法删除操作",category="error")
        return redirect(request.referrer)
    db.execute(
        'DELETE FROM cart WHERE goodid = ? AND ticketid IS NULL',
        (idnum,)
    )
    db.commit()
    flash("商品已从购物车移除")
    return redirect(request.referrer)

@bp.route('/cart')
@login_required
@shop_required
def cart():
    db=get_db()
    goods=db.execute(
        'SELECT cart.amount, goods.* FROM cart \
        INNER JOIN goods ON goods.id = cart.goodid    \
        WHERE cart.userid = ? AND cart.ticketid IS NULL',
        (g.user['id'],)
    ).fetchall()
    amount=db.execute(
        'SELECT SUM(amount*value) AS VALUE FROM (SELECT cart.amount, goods.* FROM cart INNER JOIN goods ON goods.id = cart.goodid WHERE cart.userid = ? AND cart.ticketid IS NULL)',
        (g.user['id'],)
    ).fetchone()['value']
    return render_template('shop/cart.html',goods=goods,amount=amount)

@bp.route('/emptycart',methods=['POST'])
@login_required
@shop_required
def emptycart():
    db=get_db()
    db.execute(
        'DELETE FROM cart WHERE ticketid IS NULL AND userid = ?',
        (g.user['id'],)
    )
    db.commit()
    return redirect(request.referrer)


@bp.route('/calccart',methods=['POST'])
@login_required
@shop_required
def calccart():
    db=get_db()
    goods=db.execute(
        'SELECT cart.amount, goods.* FROM cart \
        INNER JOIN goods ON goods.id = cart.goodid    \
        WHERE cart.userid = ? AND cart.ticketid IS NULL',
        (g.user['id'],)
    ).fetchall()
    if goods == []:
        flash("你的购物车是空的",category="error")
        return redirect(request.referrer)
    amount=db.execute(
        'SELECT SUM(amount*value) AS VALUE FROM (SELECT cart.amount, goods.* FROM cart INNER JOIN goods ON goods.id = cart.goodid WHERE cart.userid = ? AND cart.ticketid IS NULL)',
        (g.user['id'],)
    ).fetchone()['value']
    info=db.execute(
        'INSERT INTO ticket (address, value, userid, status) VALUES (?, ?, ?, ?)',
        (g.shopuser['address'], amount, g.user['id'],"pending",)
    )
    db.execute(
        'UPDATE cart SET ticketid = ? WHERE userid = ? AND ticketid IS NULL',
        (info.lastrowid, g.user['id'],)
    )
    db.commit()
    return redirect(request.referrer)

@bp.route('/tickets')
@login_required
@shop_required
def tickets():
    db=get_db()
    tickets=db.execute(
        'SELECT * FROM ticket WHERE userid = ?',
        (g.user['id'],)
    ).fetchall()
    info=[]
    for ticket in tickets:
        goods=db.execute(
            'SELECT * FROM cart INNER JOIN goods ON cart.goodid=goods.id WHERE ticketid = ? AND userid = ?',
            (ticket['id'],g.user['id'],)
        ).fetchall()
        info.append((ticket,goods))
    return render_template('shop/tickets.html',info=info)

@bp.route('/cancelticket/<int:idnum>',methods=['POST'])
@login_required
@shop_required
def cancelticket(idnum):
    db=get_db()
    info=db.execute(
        'SELECT status FROM ticket WHERE id = ? AND userid = ?',
        (idnum,g.user['id'],)
    ).fetchone()
    if info['status'] != "pending":
        flash("非法取消订单",category="error")
        return redirect(request.referrer)
    db.execute(
        'UPDATE ticket SET status = ? WHERE id = ? AND userid = ?',
        ("cancelled",idnum,g.user['id'],)
    )
    db.commit()
    return redirect(request.referrer)

@bp.route('/finishticket/<int:idnum>',methods=['POST'])
@login_required
@shop_required
@shop_admin_required
def finishticket(idnum):
    db=get_db()
    info=db.execute(
        'SELECT status FROM ticket WHERE id = ?',
        (idnum,)
    ).fetchone()
    if info['status'] != "pending":
        flash("非法完成订单",category="error")
        return redirect(request.referrer)
    db.execute(
        'UPDATE ticket SET status = ? WHERE id = ?',
        ("finished",idnum,)
    )
    db.commit()
    return redirect(request.referrer)

@bp.route('/configtickets')
@login_required
@shop_required
@shop_admin_required
def configtickets():
    db=get_db()
    tickets=db.execute(
        'SELECT ticket.id,ticket.address,value,created,status,phone,email,postalcode,username \
        FROM ticket INNER JOIN shopuser ON ticket.userid=shopuser.userid INNER JOIN USER ON shopuser.userid=user.id'
    ).fetchall()
    info=[]
    for ticket in tickets:
        goods=db.execute(
            'SELECT * FROM cart INNER JOIN goods ON cart.goodid=goods.id WHERE ticketid = ?',
            (ticket['id'],)
        ).fetchall()
        info.append((ticket,goods))
    return render_template('shop/configtickets.html',info=info)