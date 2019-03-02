import os

from flask import Flask

name = "nut_cloud"

def create_app(test_config=None):
    app=Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'data.sqlite'),
        PANFILE=os.path.join(app.instance_path, 'upload_files/'),
        SHOPFILE=os.path.join(app.instance_path, 'shop/'),
        RESTARTFILE=os.path.join(app.instance_path, 'restart/'),
        HOSTNAME='https://www.example.com',
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Strict',
    )

    if test_config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)
    
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    from . import db
    db.init_app(app)

    from . import auth
    app.register_blueprint(auth.bp)

    from . import pan
    app.register_blueprint(pan.bp)
    try:
        os.makedirs(app.config['PANFILE'])
    except OSError:
        pass
    
    from . import shop
    app.register_blueprint(shop.bp)
    try:
        os.makedirs(app.config['SHOPFILE'])
    except OSError:
        pass

    from . import panel
    app.register_blueprint(panel.bp)
    try:
        os.makedirs(app.config['RESTARTFILE'])
    except OSError:
        pass

    app.add_url_rule('/', endpoint='index')

    return app