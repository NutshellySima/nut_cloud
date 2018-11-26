import os
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    send_file,
    session,
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask.sessions import SessionInterface
from flask_sqlalchemy import SQLAlchemy
import datetime
import nacl.pwhash

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config.from_object(__name__)
app.secret_key = b'a5g8o1.8;5]85f5n2l5[\'65g6n-2d5d42l5d5rt'
app.config['SQLALCHEMY_DATABASE_URI'] = \
'sqlite:///'+os.path.join(basedir,'users.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

@app.route('/')
def index():
    return redirect('login')


@app.route('/upload_file', methods=['GET', 'POST'])
def upload_file():
    try:
        if 'user' not in session:
            return redirect('login')
        if request.method == 'POST':
            if 'file' not in request.files:
                return redirect(request.url)
            file = request.files.getlist("file")
            for f in file:
                file_path = os.path.abspath(
                    os.path.join('../upload_files/' + session['user'],
                                 f.filename))
                allowed_path = os.path.abspath(
                    os.path.join('../upload_files/' + session['user']))
                if allowed_path == file_path[:len(allowed_path)]:
                    while os.path.exists(file_path) and os.path.isfile(file_path):
                        sp = os.path.splitext(file_path)
                        file_path = sp[0] + ' - copy' + sp[1]
                    f.save(file_path)
    except Exception as e:
        return redirect('login')
    return render_template('upload_file.html')


@app.route('/list_file')
def list_file():
    try:
        if 'user' not in session:
            return redirect('login')
        fl = os.listdir('../upload_files/' + session['user'])
        return render_template('list_file.html', name=fl)
    except Exception:
        return redirect('login')


@app.route('/download/<path:filename>')
def download(filename):
    try:
        if 'user' not in session:
            return redirect('login')
        file_path = os.path.abspath((os.path.join(
            '../upload_files/' + session['user'], filename)))
        allowed_path = os.path.abspath(
            os.path.join('../upload_files/' + session['user']))
        if allowed_path == file_path[:len(allowed_path)]:
            return send_file(file_path)
    except Exception as e:
        print(e)
    return redirect('login')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            user = request.form['user']
            pwd = str(request.form['pwd']).encode('utf-8')
            save_users = User.query.all()
            for i in save_users:
                if user == i.user and nacl.pwhash.verify(i.pwd, pwd):
                    session['user'] = user
                    return redirect('list_file')
        except Exception:
            pass
    return render_template('login.html')


class User(db.Model):
    user = db.Column(db.String(1024), primary_key=True)
    pwd = db.Column(db.String(1024))

    def __repr__(self):
        return '<user %r>' % self.user


@app.route('/register', methods=['GET', 'POST'])
def register():
    try:
        if 'user' in session:
            if request.method == 'POST':
                db.session.add(
                    User(
                        user=str(request.form['user']),
                        pwd=nacl.pwhash.str(request.form['pwd'].encode('utf-8'))))
                if request.form['pwd'] == request.form['re_pwd']:
                    db.session.commit()
                    os.mkdir('../upload_files/' + request.form['user'])
                return redirect(request.url)
            else:
                return render_template('register.html')
    except Exception:
        pass
    return redirect('login')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('login')


@app.route('/delete/<path:filename>')
def delete_file(filename):
    try:
        if 'user' not in session:
            return redirect('login')
        file_path = os.path.abspath((os.path.join(
            '../upload_files/' + session['user'], filename)))
        allowed_path = os.path.abspath(
            os.path.join('../upload_files/' + session['user']))
        if allowed_path == file_path[:len(allowed_path)]:
            if os.path.exists(file_path):
                os.remove(file_path)
        return redirect('list_file')
    except Exception:
        return redirect(request.url)