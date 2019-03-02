from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, current_app
)
from werkzeug.exceptions import abort

from nut_cloud.auth import login_required
from nut_cloud.db import get_db
from nut_cloud.restarter import restarter

import os

bp=Blueprint('panel', __name__)

@bp.route('/')
def index():
    return render_template('panel/index.html')

@bp.route('/restart-b9b3-a760-f2ba-8784', methods=['POST'])
def restart():
    try:
        if request.headers['X-GitHub-Event'] == 'ping':
            return ('', 204)
        # FIXME: We should also prevent replay attack in header: X-GitHub-Delivery
        # FIXME: We should also prevent malicious attacks in header: X-Hub-Signature
        if request.headers['X-GitHub-Event'] == 'push':
            restarter(os.path.abspath(current_app.config['RESTARTFILE']))
            #os.spawnl(os.P_NOWAIT, '/home/sima/myproject/start.sh',
                      #'/home/sima/myproject/start.sh')
            return ('', 204)
    except Exception as e:
        print(e)
        return ('', 500)