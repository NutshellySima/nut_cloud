import os

from flask import Flask

def create_app(test_config=None):
    app=Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='ec82-502e-caf0-8bb9-1be9',
        DATABASE=os.path.join(app.instance_path, 'data.sqlite'),
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
        os.makedirs("../upload_files/")
    except OSError:
        pass
    
    from . import shop
    app.register_blueprint(shop.bp)
    try:
        os.makedirs("../upload_files/anyone/shop")
    except OSError:
        pass

    from . import panel
    app.register_blueprint(panel.bp)

    app.add_url_rule('/', endpoint='index')

    return app