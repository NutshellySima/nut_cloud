import os
import re
import shutil
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    send_file,
    session,
)
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
            dir_path = ''
            if 'dir_path' in request.values:
                dir_path = request.values['dir_path']
            if 'file' not in request.files:
                return redirect(request.url)
            file = request.files.getlist("file")
            for f in file:
                file_path = os.path.abspath(
                    os.path.join('../upload_files/',
                                 os.path.join(dir_path, f.filename)))
                anyone_path = os.path.abspath(
                    os.path.join('../upload_files/anyone'))
                allowed_path = os.path.abspath(
                    os.path.join('../upload_files/' + session['user']))
                if allowed_path == file_path[:len(allowed_path)] or\
                    anyone_path == file_path[:len(anyone_path)]:
                    while os.path.exists(file_path) and os.path.isfile(
                            file_path):
                        split_file_name = os.path.splitext(file_path)
                        file_path = split_file_name[
                            0] + ' - copy' + split_file_name[1]
                    f.save(file_path)
    except Exception:
        return redirect('login')
    dir_path = ''
    if 'dir_path' in request.values:
        dir_path = request.values['dir_path']
    return render_template(
        'upload_file.html', user=session['user'], dir_path=dir_path)


@app.route('/list_file')
def list_file():
    try:
        if 'user' not in session:
            return redirect('login')
        dir_path = ''
        if 'dir_path' in request.values:
            dir_path = request.values['dir_path']
        if dir_path != '':
            if dir_path[len(dir_path) - 1] == '/':
                dir_path = dir_path[:-1]
        else:
            dir_path = session['user']
        cur_dir_abs_path = os.path.abspath(
            os.path.join('../upload_files/', dir_path))
        allowed_path = os.path.abspath(
            os.path.join('../upload_files/' + session['user']))
        anyone_path = os.path.abspath(os.path.join('../upload_files/anyone'))
        p = re.compile('.*\\.\\.')
        if p.match(dir_path):
            cur_dir_abs_path.replace('\\', '/')
            if allowed_path == cur_dir_abs_path[:len(allowed_path)]:
                return redirect('/list_file?dir_path=' + session['user'] +
                                '/' + cur_dir_abs_path[len(allowed_path) + 1:])
            if anyone_path == cur_dir_abs_path[:len(anyone_path)]:
                return redirect('/list_file?dir_path=' + 'anyone/' +
                                cur_dir_abs_path[len(anyone_path) + 1:])
        if allowed_path != cur_dir_abs_path[:len(allowed_path)] and\
                    anyone_path != cur_dir_abs_path[:len(anyone_path)]:
            return redirect('list_file')
        file_list = os.listdir(cur_dir_abs_path)
        file_list = sorted(file_list)
        for i in range(len(file_list)):
            file_size = os.path.getsize(
                os.path.abspath(
                    os.path.join(cur_dir_abs_path, str(file_list[i]))))
            file_name = str(file_list[i])
            split_file_name = os.path.splitext(
                os.path.join(cur_dir_abs_path, str(file_list[i])))
            is_dir = os.path.isdir(
                os.path.join(cur_dir_abs_path, str(file_list[i])))
            if len(split_file_name[1]):
                file_name = file_name[:-len(split_file_name[1])]
                file_list[i] = {
                    'size': str(size(file_size)),
                    'name': file_name,
                    'ext': str(split_file_name[1][1:]),
                    'filename': file_name + "." + str(split_file_name[1][1:])
                }
            else:
                file_list[i] = {
                    'size': str(size(file_size)),
                    'name': file_name,
                    'filename': file_name
                }
            if is_dir:
                file_list[i]['is_dir'] = True
        return render_template(
            'list_file.html',
            files={
                'files': file_list,
                'dir_path': dir_path
            },
            user=session['user'])
    except Exception as e:
        print(e.args)
    return redirect('login')


@app.route('/download/<path:filename>')
def download(filename):
    try:
        if 'user' not in session:
            return redirect('login')
        file_path = os.path.abspath((os.path.join('../upload_files/',
                                                  filename)))
        allowed_path = os.path.abspath(
            os.path.join('../upload_files/' + session['user']))
        anyone_path = os.path.abspath(os.path.join('../upload_files/anyone'))
        if allowed_path == file_path[:len(allowed_path)] or\
                    anyone_path == file_path[:len(anyone_path)]:
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


@app.route('/delete')
def delete_file():
    try:
        if 'user' not in session:
            return redirect('login')
        filename = request.values['filename']
        dir_path = request.values['dir_path']
        file_path = os.path.abspath((os.path.join(
            '../upload_files/', os.path.join(dir_path, filename))))
        allowed_path = os.path.abspath(
            os.path.join('../upload_files/', session['user']))
        anyone_path = os.path.abspath(os.path.join('../upload_files/anyone'))
        print(file_path)
        if allowed_path == file_path[:len(allowed_path)] or\
                    anyone_path == file_path[:len(anyone_path)]:
            if os.path.exists(file_path):
                if os.path.isfile(file_path):
                    os.remove(file_path)
                if os.path.isdir(file_path):
                    print('rmdir')
                    if file_path != allowed_path and file_path != anyone_path:
                        shutil.rmtree(file_path)
                    else:
                        print('ban')
        if dir_path[len(dir_path) - 1] == '/':
            dir_path = dir_path[:-1]
        return redirect('list_file?dir_path=' + dir_path)
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


@app.route('/create_dir', methods=['GET', 'POST'])
def create_dir():
    if 'user' not in session:
        return redirect('login')
    if request.method == 'GET':
        dir_path = request.values['dir_path']
        return render_template(
            'create_dir.html', user=session['user'], dir_path=dir_path)
    dir_name = request.form['dir_name']
    dir_path = request.form['dir_path']
    allowed_path = os.path.abspath(
        os.path.join('../upload_files/', session['user']))
    dir_abs_path = os.path.abspath(
        os.path.join('../upload_files/', os.path.join(dir_path, dir_name)))
    anyone_path = os.path.abspath(os.path.join('../upload_files/anyone'))
    if dir_abs_path[:len(allowed_path)] == allowed_path or\
                    anyone_path == dir_abs_path[:len(anyone_path)]:
        try:
            os.mkdir(dir_abs_path)
        except Exception as e:
            pass
    return redirect('list_file?dir_path=' + dir_path)  #todo p


@app.route('/restart-b9b3-a760-f2ba-8784', methods=['POST'])
def restart():
    try:
        if request.headers['X-GitHub-Event'] == 'ping':
            return ('', 204)
        # FIXME: We should also prevent replay attack in header: X-GitHub-Delivery
        # FIXME: We should also prevent malicious attacks in header: X-Hub-Signature
        if request.headers['X-GitHub-Event'] == 'push':
            os.spawnl(os.P_NOWAIT, '/home/sima/myproject/start.sh',
                      '/home/sima/myproject/start.sh')
            return ('', 204)
    except Exception as e:
        print(e)
        return ('', 500)


@app.route('/register_log')
def register_log():
    try:
        if 'user' not in session:
            return redirect('login')
        if session['user'] == 'lemon' or session['user'] == 'smcj':
            return send_file(os.path.abspath('./register_log.txt'))
    except Exception as e:
        print(e)
    return redirect('login')


@app.route('/login_log')
def login_log():
    try:
        if 'user' not in session:
            return redirect('login')
        if session['user'] == 'lemon' or session['user'] == 'smcj':
            return send_file(os.path.abspath('./login_log.txt'))
    except Exception as e:
        print(e)
    return redirect('login')