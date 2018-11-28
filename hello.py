import os
import re
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    send_file,
    session,
)
from flask.sessions import SessionInterface
from flask_sqlalchemy import SQLAlchemy
import datetime
import nacl.pwhash
from hurry.filesize import size
import string
import random

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config.from_object(__name__)
app.secret_key = b'a5g8o1.8;5]85f5n2l5[\'65g6n-2d5d42l5d5rt'
app.config['SQLALCHEMY_DATABASE_URI'] = \
'sqlite:///'+os.path.join(basedir,'users.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


def generate_invite_code(size=6, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


@app.route('/')
def index():
    return redirect('/static/index.html')


@app.route('/pan')
@app.route('/nut_cloud')
def nut_cloud():
    if 'user' in session:
        return redirect('list_file')
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
                    while os.path.exists(file_path) and os.path.isfile(
                            file_path):
                        sp = os.path.splitext(file_path)
                        file_path = sp[0] + ' - copy' + sp[1]
                    f.save(file_path)
    except Exception:
        return redirect('login')
    return render_template('upload_file.html', user=session['user'])


@app.route('/list_file')
def list_file():
    try:
        if 'user' not in session:
            return redirect('login')
        fl = os.listdir('../upload_files/' + session['user'])
        fl = sorted(fl)
        for i in range(len(fl)):
            file_size = os.path.getsize(
                os.path.abspath(
                    os.path.join('../upload_files/' + session['user'],
                                 str(fl[i]))))
            file_name = str(fl[i])
            sp = os.path.splitext(
                os.path.join('../upload_files/' + session['user'], str(fl[i])))
            if len(sp[1]):
                file_name = file_name[:-len(sp[1])]
                fl[i] = {
                    'size': str(size(file_size)),
                    'name': file_name,
                    'ext': str(sp[1][1:]),
                    'filename': file_name + "." + str(sp[1][1:])
                }
            else:
                fl[i] = {
                    'size': str(size(file_size)),
                    'name': file_name,
                    'filename': file_name
                }
        return render_template(
            'list_file.html', files=fl, user=session['user'])
    except Exception as e:
        print(e.args)
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
            f = open('login_log.txt', mode='a+')
            user = request.form['user']
            pwd = str(request.form['pwd']).encode('utf-8')
            save_users = User.query.all()
            for i in save_users:
                if user == i.user and nacl.pwhash.verify(i.pwd, pwd):
                    session['user'] = user
                    f.write('User ' + str(user) + ' login at ' +
                            str(datetime.datetime.now()) + ' successfully.\n')
                    return redirect('list_file')
        except Exception:
            f.write('User ' + str(user) + ' login at ' +
                    str(datetime.datetime.now()) + ' failed.\n')
            pass
    if 'user' in session:
        return redirect('list_file')
    return render_template('login.html')


class User(db.Model):
    user = db.Column(db.String(1024), primary_key=True)
    pwd = db.Column(db.String(1024))

    def __repr__(self):
        return '<user %r>' % self.user


class Invite_code(db.Model):
    code = db.Column(db.String(16), primary_key=True)

    def __repr__(self):
        return '<user %r>' % self.code


@app.route('/register', methods=['GET', 'POST'])
def register():
    try:
        if 'user' in session:
            return redirect('list_file')
        if request.method == 'POST':
            f = open('register_log.txt', mode='a+')
            icode = Invite_code.query.all()
            icodel = []
            for i in range(len(icode)):
                icodel.append(icode[i].code)
            have_code = request.form['invite_code'] in icodel
            if have_code:
                db.session.add(
                    User(
                        user=str(request.form['user']),
                        pwd=nacl.pwhash.str(
                            request.form['pwd'].encode('utf-8'))))
                pattern = re.compile("[A-Za-z0-9_-]+")
                if request.form['pwd'] == request.form['re_pwd']:
                    if pattern.fullmatch(str(
                            request.form['user'])) is not None:
                        db.session.delete(
                            Invite_code.query.filter_by(
                                code=request.form['invite_code']).first())
                        db.session.commit()
                        os.mkdir('../upload_files/' + request.form['user'])
                        f.write('Someone register an account named ' +
                                request.form['user'] + ' at ' +
                                str(datetime.datetime.now()) +
                                ' successfully.\n')
                        return render_template(
                            'register_result.html', success='sucess')
        else:
            return render_template('register.html')
    except Exception as e:
        print(e.args)
    if not have_code:
        f.write('Someone do not have authority register an account named ' +
                request.form['user'] + ' at ' + str(datetime.datetime.now()) +
                ' failed.\n')
    else:
        f.write('Someone have authority register an account named ' +
                request.form['user'] + ' at ' + str(datetime.datetime.now()) +
                ' failed.\n')
    return render_template('register_result.html')


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
        return redirect('login')


@app.route('/invite', methods=['GET', 'POST'])
def invite():
    if 'user' not in session:
        return redirect('login')
    if session['user'] != 'lemon' and session['user'] != 'smcj':
        return redirect('list_file')
    if request.method == 'GET':
        return render_template('invite.html', user=session['user'])
    ivc = generate_invite_code(16)
    db.session.add(Invite_code(code=ivc))
    db.session.commit()
    return render_template(
        'invite.html', invite_code=ivc, user=session['user'])

@app.route('/restart-b9b3-a760-f2ba-8784', methods=['POST'])
def restart():
    try:
        if request.headers['X-GitHub-Event'] == 'ping':
            return ('', 204)
        # FIXME: We should also prevent replay attack in header: X-GitHub-Delivery
        # FIXME: We should also prevent malicious attacks in header: X-Hub-Signature
        if request.headers['X-GitHub-Event'] == 'push' and "/dev" in request.form['ref']:
            os.spawnl(os.P_NOWAIT, '/home/sima/myproject/start.sh','/home/sima/myproject/start.sh')
            return ('', 204)
    except Exception as e:
        print(e)
        return ('', 500)