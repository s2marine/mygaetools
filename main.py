# -*- encoding:utf-8 -*-
import sys
'lib' in sys.path or sys.path.append('lib')
import logging
logging.getLogger("requests").setLevel(logging.WARNING)

from flask import Flask, render_template, Blueprint, url_for

from rss.main import rss

app = Flask(__name__)
app.register_blueprint(rss, url_prefix='/RSS')

@app.route('/')
def main():
    return render_template('main.html')
