# nut_cloud

[![PyPI version](https://badge.fury.io/py/nut-cloud.svg)](https://badge.fury.io/py/nut-cloud)

A website featuring a easy cloud drive and an online shop.

## Feature

1. Shop
2. Cloud drive

### Database

SQLite

### Framework

Flask

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

You need to configure the `SECRET_KEY` and the `HOSTNAME` yourself!

You can put a `config.py` in the app instance folder to configure these settings.

## Language

Simplified Chinese

## License

Copyright (c) 2018-2019 Chijun Sima, Yixue Zhong

Licensed under the MIT License.