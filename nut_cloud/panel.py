from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, current_app
)
from werkzeug.exceptions import abort

from nut_cloud.auth import login_required
from nut_cloud.db import get_db
from nut_cloud.restarter import restarter,verifyrestart

import os

bp=Blueprint('panel', __name__)

@bp.route('/')
def index():
    return render_template('panel/index.html')

@bp.route('/restart-b9b3-a760-f2ba-8784', methods=['POST'])
def restart():
    if not verifyrestart(request.get_data(),current_app.config['WEBHOOK_SECRET_KEY'],request.headers['X-Hub-Signature']):
        abort(403)
    try:
        if request.headers['X-GitHub-Event'] == 'ping':
            return ('', 204)
        if request.headers['X-GitHub-Event'] == 'push':
            restarter(os.path.abspath(current_app.config['RESTARTFILE']))
            return ('', 204)
    except Exception as e:
        print(e)
        return ('', 500)