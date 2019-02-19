import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from zxcvbn import zxcvbn
import nacl.pwhash

from nut_cloud.db import get_db

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username=request.form['username']
        password=request.form['password']
        db=get_db()
        error=None

        if not username:
            error='Username is required.'
        elif not password:
            error='Password is required.'
        elif db.execute(
            'SELECT id FROM user WHERE username = ?', (username,)
        ).fetchone() is not None:
            error = 'User {} is already registered.'.format(username)
        elif zxcvbn(str(password), user_inputs=[str(username)])['score']<1:
            error = "Insufficient password strength."
        
        if error is None:
            all_user=None
            all_user=db.execute(
                'SELECT * FROM user'
            ).fetchone()
            if all_user is None:
                db.execute(
                    'INSERT INTO user (username, password, isadmin) VALUES (?, ?, ?)',
                    (username, nacl.pwhash.str(password.encode('utf-8')), 1)
                )
            else:
                db.execute(
                    'INSERT INTO user (username, password, isadmin) VALUES (?, ?, ?)',
                    (username, nacl.pwhash.str(password.encode('utf-8')), 0)
                )
            db.commit()
            return redirect(url_for('auth.login'))
        
        flash(error,category="error")

    return render_template('auth/register.html')

@bp.route('login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username=request.form['username']
        password=request.form['password']
        db=get_db()
        error=None
        user=db.execute(
            'SELECT * FROM user WHERE username = ?',
            (username,)
        ).fetchone()

        if user is None:
            error = 'Incorrect username.'
        else:
            try:
                nacl.pwhash.verify(user['password'], password.encode('utf-8'))
            except nacl.exceptions.InvalidkeyError:
                error = 'Incorrect password.'
                db.execute(
                    'INSERT INTO logs (userid, title, body) VALUES (?, ?, ?)',
                    (user['id'], "auth.login.failed", "Somebody failed to login your account.")
                )
                db.commit()
        
        if error is None:
            session.clear()
            session['user_id']=user['id']
            db.execute(
                'INSERT INTO logs (userid, title, body) VALUES (?, ?, ?)',
                (user['id'], "auth.login.success", "You logged in the system successfully.")
            )
            db.commit()
            return redirect(url_for('index'))
        
        flash(error,category="error")
    
    return render_template('auth/login.html')

@bp.before_app_request
def load_logged_in_user():
    user_id=session.get('user_id')

    if user_id is None:
        g.user=None
        g.shopuser=None
        g.panuser=None
    else:
        db=get_db()
        g.user=db.execute(
            'SELECT * FROM user WHERE id = ?',
            (user_id,)
        ).fetchone()
        g.shopuser = db.execute(
            'SELECT * FROM shopuser WHERE userid = ?',
            (g.user['id'],)
        ).fetchone()
        g.panuser=db.execute(
            'SELECT * FROM panuser WHERE userid = ?',
            (g.user['id'],)
        ).fetchone()

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash("您尚未登陆",category="error")
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view

@bp.route('/logout', methods=['POST'])
@login_required
def logout():
    db=get_db()
    db.execute(
        'INSERT INTO logs (userid, title, body) VALUES (?, ?, ?)',
        (g.user['id'], "auth.logout", "You logged out the system.")
    )
    db.commit()
    session.clear()
    return redirect(url_for('index'))

@bp.route('/settings', methods=['GET'])
@login_required
def settings():
    db=get_db()
    logs=db.execute(
        'SELECT * FROM logs WHERE userid = ? ORDER BY created DESC',
        (g.user['id'],)
    ).fetchall()
    return render_template('auth/settings.html', logs=logs)

@bp.route('/registerAdmin', methods=['POST'])
@login_required
def registerAdmin():
    isAdmin=int(g.user['isadmin'])
    if isAdmin == 0:
        return redirect(url_for('auth.settings'))
    else:
        db=get_db()
        user=db.execute(
            'SELECT id FROM user WHERE username = ?',
            (request.form['username'],)
        ).fetchone()
        if user is None:
            return redirect(url_for('auth.settings'))
        db.execute(
            'UPDATE user SET isadmin = ? WHERE id = ?',
            (1, user['id'],)
        )
        db.execute(
            'INSERT INTO logs (userid, title, body) VALUES (?, ?, ?)',
            (user['id'], "auth.registerAdmin", "You are registered as Admin in the cardinal system.")
        )
        db.commit()
        return redirect(url_for('auth.settings'))

@bp.route('/registerPan', methods=['POST'])
@login_required
def registerPan():
    isAdmin=int(g.user['isadmin'])
    if isAdmin == 0:
        return redirect(url_for('auth.settings'))
    else:
        db=get_db()
        user=db.execute(
            'SELECT * FROM user WHERE username = ?',
            (request.form['username'],)
        ).fetchone()
        if user is None:
            return redirect(url_for('auth.settings'))
        currentUser=db.execute(
            'SELECT * FROM panuser WHERE userid = ?',
            (user['id'],)
        ).fetchone()
        if currentUser is not None:
            error='User {} is already granted disk access.'.format(user['username'])
            flash(error,category="error")
            return redirect(url_for('auth.settings'))
        db.execute(
            'INSERT INTO panuser (userid) VALUES (?)',
            (user['id'],)
        )
        db.execute(
            'INSERT INTO logs (userid, title, body) VALUES (?, ?, ?)',
            (user['id'], "auth.registerPan", "You are granted disk access.")
        )
        db.commit()
        return redirect(url_for('auth.settings'))