from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, send_file,current_app
)
from werkzeug.exceptions import abort
from werkzeug.utils import secure_filename
import qrcode
import base64
import nacl.pwhash
import datetime
import tarfile
import tempfile
from tempfile import NamedTemporaryFile
from nut_cloud.auth import login_required
from nut_cloud.db import get_db
import os
import shutil
import weakref
import glob
import functools
from hurry.filesize import size

bp = Blueprint('pan', __name__, url_prefix='/pan')
basedir = os.path.abspath(os.path.dirname(__file__))


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
        except Exception:
            pass


file_remover = FileRemover()


def pan_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.panuser is None:
            flash("你没有网盘访问权限",category="error")
            return redirect(url_for('index'))
        try:
            os.makedirs(os.path.join(current_app.config['PANFILE'], secure_filename(g.user['username'])))
        except OSError:
            pass
        try:
            os.makedirs(os.path.join(current_app.config['PANFILE'],"anyone/"))
        except OSError:
            pass
        return view(**kwargs)

    return wrapped_view

def DirAisinDirB(DirA, DirB):
    return os.path.commonpath([os.path.abspath(DirA), os.path.abspath(DirB)]) == DirB
def requestedAbsPath(path):
    if path is None:
        path=''
    ret_path=os.path.abspath(os.path.join(current_app.config['PANFILE'], path))
    if not DirAisinDirB(ret_path,os.path.abspath(current_app.config['PANFILE'])):
        abort(403)
    return ret_path
def makeUserDirAbsPath(user):
    user_path=os.path.abspath(os.path.join(current_app.config['PANFILE'], secure_filename(user)))
    if not DirAisinDirB(user_path,requestedAbsPath(None)):
        abort(403)
    return user_path
def isAnyoneRequest(requestedPath):
    return DirAisinDirB(requestedPath, makeUserDirAbsPath("anyone"))
def isNotRoot(requestedPath, realUser):
    return not (os.path.samefile(requestedPath, makeUserDirAbsPath(realUser)) or os.path.samefile(requestedPath, makeUserDirAbsPath("anyone")))
def isValidRequest(requestedPath, realUser):
    return DirAisinDirB(requestedPath, makeUserDirAbsPath(realUser)) or DirAisinDirB(requestedPath, makeUserDirAbsPath("anyone"))
def whichUserRequest(requestedPath, realUser):
    if not isValidRequest(requestedPath, realUser):
        abort(403)
    if isAnyoneRequest(requestedPath):
        return "anyone"
    return realUser

@bp.route('/')
@login_required
@pan_required
def index():
    return redirect(url_for('pan.list_file',dir_path=g.user['username']))

@bp.route('/list_file')
@login_required
@pan_required
def list_file():
    dir_path=request.values.get('dir_path')
    requestedPath=requestedAbsPath(dir_path)
    if not isValidRequest(requestedPath,g.user['username']):
        return redirect(url_for('pan.list_file',dir_path=g.user['username']))
    file_list=sorted(os.listdir(requestedPath))
    
    def processFile(file):
        fileAbsPath=os.path.join(requestedPath, str(file))
        file_size=str(size(os.path.getsize(fileAbsPath)))
        name=file_name=str(file)
        split_file_name = os.path.splitext(fileAbsPath)
        is_dir=os.path.isdir(fileAbsPath)
        if not is_dir and split_file_name[1][1:]:
            name=file_name[:-len(split_file_name[1])]
        ext=str(split_file_name[1][1:])
        return {
            'size':file_size,
            'name':name,
            'ext':ext,
            'filename':file_name,
            'is_dir':is_dir
        }
    whichUser= whichUserRequest(requestedPath,g.user['username'])
    dir_path=whichUser+"/"+os.path.relpath(requestedPath,makeUserDirAbsPath(whichUser))
    file_list=list(map(processFile, file_list))
    return render_template('pan/index.html',files={
        'files':file_list,
        'dir_path':dir_path
    })

@bp.route('/upload_file', methods=['POST'])
@login_required
@pan_required
def upload_file():
    dir_path=request.values.get('dir_path')
    requestedPath=requestedAbsPath(dir_path)
    if not isValidRequest(requestedPath,g.user['username']):
        return redirect(request.referrer)
    if 'file' not in request.files:
        flash('No file part',category="error")
        return redirect(request.referrer)
    files = request.files.getlist("file")
    for file in files:
        path=os.path.join(requestedPath, file.filename)
        if not isValidRequest(os.path.abspath(path),g.user['username']):
            continue
        while os.path.exists(path) and os.path.isfile(path):
            split_file_name = os.path.splitext(path)
            path = split_file_name[0] + '-copy' + split_file_name[1]
        file.save(path)
    return redirect(request.referrer)

@bp.route('/tar')
@login_required
@pan_required
def tar():
    requestedPath=requestedAbsPath(request.values.get('dir_path'))
    whichUser= whichUserRequest(requestedPath,g.user['username'])
    dir_path=whichUser+"/"+os.path.relpath(requestedPath,makeUserDirAbsPath(whichUser))
    if not isValidRequest(requestedPath,g.user['username']):
        return redirect(request.referrer)
    tempdir = tempfile.mkdtemp()
    def reset(tarinfo):
        tarinfo.uid = tarinfo.gid = 0
        tarinfo.uname = tarinfo.gname = g.user['username']
        return tarinfo
    tarpath=os.path.join(tempdir, dir_path.split('/')[-1]+".tar")
    tar = tarfile.open(tarpath, "w")
    tar.add(requestedPath, dir_path.split('/')[-1], filter=reset)
    tar.close()
    resp = send_file(tarpath,as_attachment=True)
    file_remover.cleanup_once_done(resp, tempdir)
    return resp


@bp.route('/create_dir', methods=['GET', 'POST'])
@login_required
@pan_required
def create_dir():
    if request.method == 'GET':
        dir_path = request.values['dir_path']
        return render_template('pan/create_dir.html', dir_path=dir_path)
    dir_name = request.form['dir_name']
    dir_path = request.form['dir_path']
    requestedPath=requestedAbsPath(os.path.join(dir_path,dir_name))
    if not isValidRequest(requestedPath,g.user['username']):
        return redirect(request.referrer)
    try:
        os.mkdir(requestedPath)
    except Exception:
        pass
    return redirect(url_for('pan.list_file',dir_path=dir_path))

@bp.route('/search')
@login_required
@pan_required
def search():
    dir_path=request.values.get('dir_path')
    requestedPath=requestedAbsPath(dir_path)
    if not isValidRequest(requestedPath,g.user['username']):
        return redirect(url_for('pan.list_file',dir_path=g.user['username']))
    search_name=request.values.get('search_name')
    file_list = sorted(glob.glob(requestedPath+"/**/*"+glob.escape(search_name)+"*",recursive=True))
    file_list=[i for i in file_list if os.path.commonpath([os.path.abspath(i),requestedPath]) == requestedPath]
    whichUser= whichUserRequest(requestedPath,g.user['username'])
    dir_path=whichUser+"/"+os.path.relpath(requestedPath,makeUserDirAbsPath(whichUser))
    def processFile(file):
        fileAbsPath=os.path.abspath(file)
        name=file_name=os.path.relpath(fileAbsPath,makeUserDirAbsPath(whichUser))
        file_size=str(size(os.path.getsize(fileAbsPath)))
        split_file_name = os.path.splitext(fileAbsPath)
        is_dir=os.path.isdir(fileAbsPath)
        if not is_dir and split_file_name[1][1:]:
            name=file_name[:-len(split_file_name[1])]
        ext=str(split_file_name[1][1:])
        return {
            'size':file_size,
            'name':name,
            'ext':ext,
            'filename':file_name,
            'is_dir':is_dir
        }
    
    file_list=list(map(processFile, file_list))
    return render_template('pan/index.html',files={
        'files':file_list,
        'dir_path':dir_path
    })


@bp.route('/download/<path:filename>')
@login_required
@pan_required
def download(filename):
    requestedPath=requestedAbsPath(filename)
    if not isValidRequest(requestedPath,g.user['username']):
        return redirect(url_for('pan.list_file',dir_path=g.user['username']))
    return send_file(requestedPath,as_attachment=True,conditional=True)

@bp.route('/delete', methods=['POST'])
@login_required
@pan_required
def delete_file():
    filename = request.values['filename']
    dir_path = request.values['dir_path']
    file_path=requestedAbsPath(os.path.join(dir_path, filename))
    error=None
    if not isValidRequest(file_path,g.user['username']):
        error="正在删除非法文件"
    elif not os.path.exists(file_path):
        error="文件不存在"
    if error is not None:
        flash(error,category="error")
        return redirect(url_for('pan.list_file',dir_path=dir_path))
    db=get_db()
    if os.path.isfile(file_path):
        os.remove(file_path)
        db.execute(
            'DELETE FROM share_info WHERE filename = ?',
            (file_path,)
        )
    elif os.path.isdir(file_path) and isNotRoot(file_path,g.user['username']):
        file_list = glob.glob(file_path+"/**/*",recursive=True)
        for file in file_list:
            db.execute(
                'DELETE FROM share_info WHERE filename = ?',
                (file,)
            )
        shutil.rmtree(file_path)
    db.commit()
    return redirect(url_for('pan.list_file',dir_path=dir_path))

# Qrcode
def serve_pil_image(pil_img):
    img_io=NamedTemporaryFile(mode='w+b', suffix='jpg')
    pil_img.save(img_io, 'JPEG', quality=95)
    img_io.seek(0, 0)
    return send_file(img_io, mimetype='image/jpeg')

@bp.route('/qrcode')
@login_required
@pan_required
def genqrcode():
    qr=qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H,
    )
    qr.add_data(current_app.config['HOSTNAME']+'/pan/s?link='+request.values['link'])
    qr.make(fit=True)
    img=qr.make_image()
    return serve_pil_image(img)

@bp.route('/shares')
@login_required
@pan_required
def shares():
    db=get_db()
    info=db.execute(
        'SELECT * FROM share_info WHERE userid = ?',
        (g.user['id'],)
    ).fetchall()
    shareLinks=[]
    for i in info:
        rel_path=os.path.relpath(i['filename'],current_app.config['PANFILE'])
        Pass=i['password'] is not None
        shareLinks.append((i['link'],rel_path,str(i['expiretime']), Pass))
    return render_template('pan/shares.html',links=shareLinks)

def generateRandomCode():
    return base64.urlsafe_b64encode(os.urandom(16)).decode('utf-8')

@bp.route('/share',methods=['GET','POST'])
@login_required
@pan_required
def share():
    if request.method == 'GET':
        dir_path = request.values['dir_path']
        return render_template('pan/share.html', path=dir_path)
    filename=request.values['filename']
    file_path=requestedAbsPath(filename)
    error=None
    if not isValidRequest(file_path,g.user['username']):
        error="正在分享非法文件"
    if error is not None:
        flash(error,category="error")
        return redirect(request.referrer)
    shareLink=generateRandomCode()
    db=get_db()
    db.execute(
        'INSERT INTO share_info (link, filename, userid) VALUES (?, ?, ?)',
        (shareLink,file_path,g.user['id'],)
    )
    if request.values['time']!='':
        t=datetime.datetime.utcnow()
        delta=datetime.timedelta(days=int(request.values['time']))
        t=t+delta
        db.execute(
            'UPDATE share_info SET expiretime = ? WHERE link = ?',
            (t, shareLink,)
        )
    if request.values['password']!='':
        password=nacl.pwhash.str(request.form['password'].encode('utf-8'))
        db.execute(
            'UPDATE share_info SET password = ? WHERE link = ?',
            (password, shareLink,)
        )
    db.commit()
    return render_template('pan/share.html',share_link=shareLink,hostname=current_app.config['HOSTNAME']),201


@bp.route('/delete_link', methods=['POST'])
@login_required
@pan_required
def delete_link():
    db=get_db()
    info=db.execute(
        'SELECT * FROM share_info WHERE link = ?',
        (request.values['link'],)
    ).fetchone()
    if info['userid']!=g.user['id']:
        flash("非法操作",category="error")
        return redirect(request.referrer)
    db.execute(
        'DELETE FROM share_info WHERE link = ?',
        (request.values['link'],)
    )
    db.commit()
    return redirect(url_for('pan.shares'))

@bp.route('/s')
def s():
    db=get_db()
    info=db.execute(
        'SELECT * FROM share_info WHERE link = ?',
        (request.values['link'],)
    ).fetchone()
    if info is None:
        abort(404)
    if info['expiretime'] is not None and datetime.datetime.utcnow()>info['expiretime']:
        flash("分享链接已过期",category="error")
        return redirect(url_for('index'))
    if info['password'] is not None:
        return render_template('pan/safeshare.html', link=request.values['link'])
    return send_file(info['filename'],as_attachment=True,conditional=True)

@bp.route('/safes', methods=['POST'])
def safes():
    db=get_db()
    info=db.execute(
        'SELECT * FROM share_info WHERE link = ?',
        (request.values['link'],)
    ).fetchone()
    if info is None:
        abort(404)
    if info['expiretime'] is not None and datetime.datetime.utcnow()>info['expiretime']:
        flash("分享链接已过期",category="error")
        return redirect(url_for('index'))
    if info['password'] is None:
        flash("该文件无密码",category="error")
        return redirect(url_for('index'))
    try:
        nacl.pwhash.verify(info['password'],str(request.form['password']).encode('utf-8'))
        return send_file(info['filename'],as_attachment=True,conditional=True)
    except Exception:
        abort(403)