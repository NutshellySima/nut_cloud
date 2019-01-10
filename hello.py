import os
import re
import shutil
import tempfile
import weakref
import tarfile
import glob
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    send_file,
    session,
    g,
    make_response,
)
from flask_sqlalchemy import SQLAlchemy
import datetime
import nacl.pwhash
from hurry.filesize import size
import string
import random
import base64

class FileRemover(object):
    def __init__(self):
        self.weak_references = dict()  # weak_ref -> filepath to remove

    def cleanup_once_done(self, response, filepath):
        wr = weakref.ref(response, self._do_cleanup)
        self.weak_references[wr] = filepath

    def _do_cleanup(self, wr):
        filepath = self.weak_references[wr]
        print('Deleting %s' % filepath)
        try:
            shutil.rmtree(filepath)
        except Exception as e:
            f = open('delete_log.txt', mode='a+')
            f.write(filepath)
            f.close()

file_remover = FileRemover()

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config.from_object(__name__)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Strict',
)
try:
    if os.environ['FLASK_ENV'] != 'development':
        app.config.update(SESSION_COOKIE_SECURE=True,)
except Exception:
    app.config.update(SESSION_COOKIE_SECURE=True,)
app.secret_key = b'a5g8o1.3;5]85f5n2l5[\'65g8n-2d5d42l5d5rt'
app.config['SQLALCHEMY_DATABASE_URI'] = \
'sqlite:///'+os.path.join(basedir,'users.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class User(db.Model):
    user = db.Column(db.String(1024), primary_key=True)
    pwd = db.Column(db.String(1024))

    def __repr__(self):
        return '<user %r>' % self.user


class Invite_code(db.Model):
    code = db.Column(db.String(16), primary_key=True)

    def __repr__(self):
        return '<user %r>' % self.code

class Share_Info(db.Model):
    link = db.Column(db.String(100), primary_key=True)
    filename = db.Column(db.String(300), nullable=False)
    username = db.Column(db.String(10), nullable=False)
    passwd = db.Column(db.String(1024), nullable=True)
    expiret = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return '<Share_Info %r>' % self.link

db.create_all()
db.session.commit()

def GetCspNonce():
  """Returns a random nonce."""
  NONCE_LENGTH = 16
  return base64.b64encode(os.urandom(NONCE_LENGTH))

# Generate a secret nonce
@app.before_request
def gen_nonce():
    g.nonce = GetCspNonce().decode('utf-8')

# Add CSP to prevent XSS attacks
@app.after_request
def add_header(response):
    if 'Content-Security-Policy' not in response.headers:
        try:
            # Production
            if os.environ['FLASK_ENV'] != 'development':
                response.headers['Content-Security-Policy'] = "upgrade-insecure-requests; block-all-mixed-content; style-src 'nonce-"+g.nonce+"' https:; script-src 'strict-dynamic' 'nonce-"+g.nonce+"' https:; object-src 'none'; base-uri 'none';"
            # Development
            else:
                response.headers['Content-Security-Policy'] = "style-src 'nonce-"+g.nonce+"' http: https:; script-src 'strict-dynamic' 'nonce-"+g.nonce+"' http: https:; object-src 'none'; base-uri 'none';"
        # Production
        except Exception:
            response.headers['Content-Security-Policy'] = "upgrade-insecure-requests; block-all-mixed-content; style-src 'nonce-"+g.nonce+"' https:; script-src 'strict-dynamic' 'nonce-"+g.nonce+"' https:; object-src 'none'; base-uri 'none';"    
    return response


def generate_invite_code():
    return GetCspNonce().decode('utf-8')


@app.route('/')
def index():
    return redirect('/static/index.html')


@app.route('/pan')
@app.route('/nut_cloud')
def nut_cloud():
    if 'user' in session:
        return redirect('list_file')
    return redirect('login')


@app.route('/upload_file', methods=['POST'])
def upload_file():
    try:
        if 'user' not in session:
            return redirect('login')
        if request.method == 'POST':
            dir_path = ''
            if 'dir_path' in request.values:
                dir_path = request.values['dir_path']
            if 'file' not in request.files:
                return redirect(request.referrer)
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
    return redirect(request.referrer)



@app.route('/shares')
def shares():
    try:
        if 'user' not in session:
            return redirect('login')
        info=Share_Info.query.filter_by(username=session['user'])
        sls=[]
        for i in info:
            rel_path=os.path.relpath(i.filename,'../upload_files/')
            sls.append((i.link,rel_path,str(i.expiret)))
        return render_template(
            'shares.html',
            user=session['user'],nonce=g.nonce,links=sls)
    except Exception as e:
        print(e.args)
    return redirect('login')

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
            user=session['user'],nonce=g.nonce)
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
            return send_file(file_path,as_attachment=True,conditional=True)
    except Exception as e:
        print(e)
    return redirect('login')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            f = open('login_log.txt', mode='a+')
            user = request.form['user']
            if user in ['anyone']:
                return redirect('login')
            pwd = str(request.form['pwd']).encode('utf-8')
            save_users = User.query.all()
            for i in save_users:
                if user == i.user and nacl.pwhash.verify(i.pwd, pwd):
                    session['user'] = user
                    f.write('User ' + str(user) + ' login at ' +
                            str(datetime.datetime.now() + datetime.timedelta(
                                hours=8)) + ' successfully.\n')
                    return redirect('list_file')
        except Exception:
            f.write('User ' + str(user) + ' login at ' +
                    str(datetime.datetime.now() +
                        datetime.timedelta(hours=8)) + ' failed.\n')
            pass
        finally:
            f.close()
    if 'user' in session:
        return redirect('list_file')
    return render_template('login.html',nonce=g.nonce)



@app.route('/register', methods=['GET', 'POST'])
def register():
    try:
        f = open('register_log.txt', mode='a+')
        if 'user' in session:
            return redirect('list_file')
        if request.method == 'POST':
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
                                str(datetime.datetime.now() +
                                    datetime.timedelta(hours=8)) +
                                ' successfully.\n')
                        return render_template(
                            'register_result.html', success='sucess',nonce=g.nonce),201
        else:
            return render_template('register.html',nonce=g.nonce)
    except Exception as e:
        print(e.args)
    finally:
        f.close()
    f = open('register_log.txt', mode='a+')
    if not have_code:
        f.write('Someone do not have authority register an account named ' +
                request.form['user'] + ' at ' +
                str(datetime.datetime.now() + datetime.timedelta(hours=8)) +
                ' failed.\n')
    else:
        f.write('Someone have authority register an account named ' +
                request.form['user'] + ' at ' +
                str(datetime.datetime.now() + datetime.timedelta(hours=8)) +
                ' failed.\n')
    f.close()
    return render_template('register_result.html',nonce=g.nonce),403


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    r=make_response(redirect('login'))
    # Try to remove all persistant XSS attacks.
    r.headers.set('Clear-Site-Data', '"*"')
    return r


@app.route('/delete', methods=['POST'])
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
                    si=Share_Info.query.filter_by(filename=file_path)
                    for i in si:
                        db.session.delete(i)
                    db.session.commit()
                if os.path.isdir(file_path):
                    print('rmdir')
                    if file_path != allowed_path and file_path != anyone_path:
                        file_list = glob.glob(file_path+"/**/*",recursive=True)
                        for i in file_list:
                            si=Share_Info.query.filter_by(filename=i)
                            for i in si:
                                db.session.delete(i)
                        db.session.commit()
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
        return render_template('invite.html', user=session['user'],nonce=g.nonce)
    ivc = generate_invite_code()
    db.session.add(Invite_code(code=ivc))
    db.session.commit()
    return render_template(
        'invite.html', invite_code=ivc, user=session['user'],nonce=g.nonce),201

@app.route('/share',methods=['GET','POST'])
def share():
    if 'user' not in session:
        return redirect('login')
    if request.method == 'GET':
        dir_path = request.values['dir_path']
        return render_template('share.html', user=session['user'],path=dir_path,nonce=g.nonce)
    filename=request.values['filename']
    file_path = os.path.abspath((os.path.join('../upload_files/',
                                                  filename)))
    allowed_path = os.path.abspath(
            os.path.join('../upload_files/' + session['user']))
    anyone_path = os.path.abspath(os.path.join('../upload_files/anyone'))
    if allowed_path == file_path[:len(allowed_path)] or\
                anyone_path == file_path[:len(anyone_path)]:
        sl = generate_invite_code()
        si=Share_Info(link=sl,filename=file_path,username=request.values['user'])
        if request.values['time']!='':
            t=datetime.datetime.utcnow()
            delta=datetime.timedelta(days=int(request.values['time']))
            t=t+delta
            si.expiret=t
        if request.values['pwd']!='':
            si.passwd=nacl.pwhash.str(
                            request.form['pwd'].encode('utf-8'))
        db.session.add(si)
        db.session.commit()
        return render_template(
            'share.html', user=session['user'],nonce=g.nonce,share_link=sl),201
    else:
        return redirect('list_file')


@app.route('/s')
def s():
    si=Share_Info.query.filter_by(link=request.values['link']).first()
    if si.expiret!=None:
        if datetime.datetime.utcnow()>si.expiret:
            return redirect('list_file')
    if si.passwd!=None:
        return render_template(
            'safedownload.html', user=session['user'], link=request.values['link'],nonce=g.nonce)
    return send_file(si.filename,as_attachment=True,conditional=True)

@app.route('/ss', methods=['POST'])
def ss():
    si=Share_Info.query.filter_by(link=request.values['link']).first()
    if si.expiret!=None:
        if datetime.datetime.utcnow()>si.expiret:
            return redirect('list_file')
    if si.passwd==None:
        return redirect('list_file')
    if nacl.pwhash.verify(si.passwd,str(request.form['pwd']).encode('utf-8')):
        return send_file(si.filename,as_attachment=True,conditional=True)
    return redirect('list_file')


@app.route('/delete_link', methods=['POST'])
def delete_link():
    try:
        if 'user' not in session:
            return redirect('login')
        si=Share_Info.query.filter_by(link=request.values['link']).first()
        if session['user']!=si.username:
            return redirect('login')
        db.session.delete(si)
        db.session.commit()
    except Exception as e:
        print(e.args)
    return redirect('login')

@app.route('/create_dir', methods=['GET', 'POST'])
def create_dir():
    if 'user' not in session:
        return redirect('login')
    if request.method == 'GET':
        dir_path = request.values['dir_path']
        return render_template(
            'create_dir.html', user=session['user'], dir_path=dir_path,nonce=g.nonce)
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
    return redirect('list_file')


@app.route('/login_log')
def login_log():
    try:
        if 'user' not in session:
            return redirect('login')
        if session['user'] == 'lemon' or session['user'] == 'smcj':
            return send_file(os.path.abspath('./login_log.txt'))
    except Exception as e:
        print(e)
    return redirect('list_file')


@app.route('/list_user')
def list_user():
    try:
        if 'user' not in session:
            return redirect('login')
        if session['user'] == 'lemon' or session['user'] == 'smcj':
            save_users = sorted(User.query.all(), key=lambda u: u.user)
            list_user_name = ''
            for i in save_users:
                list_user_name += i.user + '<br>'
            return str(list_user_name)
    except Exception as e:
        print(e)
    return redirect('list_file')


@app.route('/list_invite_code')
def list_invite_code():
    try:
        if 'user' not in session:
            return redirect('login')
        if session['user'] == 'lemon' or session['user'] == 'smcj':
            ic = sorted(Invite_code.query.all(), key=lambda u: u.code)
            licc = ''
            for i in ic:
                licc += i.code + '<br>'
            return str(licc)
    except Exception as e:
        print(e)
    return redirect('list_file')

@app.route('/tar')
def tar():
    try:
        # Check login
        if 'user' not in session:
            return redirect('login')
        dir_path = ''
        if 'dir_path' in request.values:
            dir_path = request.values['dir_path']
        # Pop '/'
        if dir_path != '':
            if dir_path[len(dir_path) - 1] == '/':
                dir_path = dir_path[:-1]
        else:
            # Set dir to user dir
            dir_path = session['user']
        # Check validity
        cur_dir_abs_path = os.path.abspath(
            os.path.join('../upload_files/', dir_path))
        allowed_path = os.path.abspath(
            os.path.join('../upload_files/' + session['user']))
        anyone_path = os.path.abspath(os.path.join('../upload_files/anyone'))
        # Windows
        p = re.compile('.*\\.\\.')
        if p.match(dir_path):
            cur_dir_abs_path.replace('\\', '/')
            if allowed_path == cur_dir_abs_path[:len(allowed_path)]:
                return redirect('/tar?dir_path=' + session['user'] +
                                '/' + cur_dir_abs_path[len(allowed_path) + 1:])
            if anyone_path == cur_dir_abs_path[:len(anyone_path)]:
                return redirect('/tar?dir_path=' + 'anyone/' +
                                cur_dir_abs_path[len(anyone_path) + 1:])
        # Invalid
        if allowed_path != cur_dir_abs_path[:len(allowed_path)] and\
                    anyone_path != cur_dir_abs_path[:len(anyone_path)]:
            return redirect('tar')

        tempdir = tempfile.mkdtemp()
        def reset(tarinfo):
            tarinfo.uid = tarinfo.gid = 0
            tarinfo.uname = tarinfo.gname = session['user']
            return tarinfo
        tarpath=os.path.join(tempdir, dir_path.split('/')[-1]+".tar")
        tar = tarfile.open(tarpath, "w")
        tar.add(cur_dir_abs_path, dir_path.split('/')[-1], filter=reset)
        tar.close()
        resp = send_file(tarpath,as_attachment=True)
        file_remover.cleanup_once_done(resp, tempdir)
        return resp
    except Exception as e:
        pass
    return redirect('login')

@app.route('/delete_log')
def delete_log():
    try:
        if 'user' not in session:
            return redirect('login')
        if session['user'] == 'lemon' or session['user'] == 'smcj':
            return send_file(os.path.abspath('./delete_log.txt'))
    except Exception as e:
        print(e)
    return redirect('list_file')

@app.route('/logs')
def logs():
    try:
        if 'user' not in session:
            return redirect('login')
        if session['user'] == 'lemon' or session['user'] == 'smcj':
            return render_template('logs.html',user=session['user'],nonce=g.nonce)
    except Exception as e:
        print(e)
    return redirect('list_file')

@app.route('/search')
def search():
    try:
        if 'user' not in session:
            return redirect('login')
        dir_path = ''
        search_name=''
        if 'search_name' in request.values:
            search_name = request.values['search_name']
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
                return redirect('/search?dir_path=' + session['user'] +
                                '/' + cur_dir_abs_path[len(allowed_path) + 1:])
            if anyone_path == cur_dir_abs_path[:len(anyone_path)]:
                return redirect('/search?dir_path=' + 'anyone/' +
                                cur_dir_abs_path[len(anyone_path) + 1:])
        if allowed_path != cur_dir_abs_path[:len(allowed_path)] and\
                    anyone_path != cur_dir_abs_path[:len(anyone_path)]:
            return redirect('list_file')
        file_list = glob.glob(cur_dir_abs_path+"/**/*"+glob.escape(search_name)+"*",recursive=True)
        file_list = sorted(file_list)
        file_list=[i for i in file_list if os.path.commonpath([os.path.abspath(i),cur_dir_abs_path]) == cur_dir_abs_path]
        for i in range(len(file_list)):
            file_list[i]=os.path.abspath(file_list[i])
            file_list[i]=os.path.relpath(file_list[i],cur_dir_abs_path)
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
            user=session['user'],nonce=g.nonce)
    except Exception as e:
        print(e.args)
    return redirect('login')
