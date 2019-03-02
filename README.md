# nut_cloud

[![PyPI version](https://badge.fury.io/py/nut-cloud.svg)](https://badge.fury.io/py/nut-cloud)

an online shop and a cloud drive using SQLite, Flask as the backend and the Bootstrap framework to ameliorate the appearance of the frontend.

## Usage

### The first time

1. `pip install nut-cloud`
2. + For Linux/macos/BSDs: `$ export FLASK_APP="nut_cloud"`
   + For Windows Powershell: `$ $env:FLASK_APP="nut_cloud"`
3. `$ flask init-db` (Only needed on the first time running nut_cloud)
4. `$ flask run`

### Later

`$ python -c 'import nut_cloud; nut_cloud.create_app().run()'`

## CAUTION

You need to configure the `SECRET_KEY`, `WEBHOOK_SECRET_KEY` and the `HOSTNAME` yourself!

You can put a `config.py` in the app instance folder to configure these settings.

## Auto deploy

You can configure your `WEBHOOK_SECRET_KEY` to match the secret key of Github Webhooks, 
then you can use Systemd to monitor file changes under `{instance path}/restart/` and 
restart the `uwsgi` server each time any file is changed.

## Language

Simplified Chinese

## License

Copyright (c) 2018-2019 Chijun Sima, Yixue Zhong

Licensed under the MIT License.