# -*- encoding:utf-8 -*-
import sys
'lib' in sys.path or sys.path.append('lib')
import logging

from google.appengine.ext import ndb
from google.appengine.api import users

from flask import Blueprint, render_template, url_for, request, redirect, Response
from rss_utils import RSSHelper, DBRSS, RSSFlag
from utils import set_deadline, islocal

from datetime import datetime, timedelta
import json
from urlparse import urlparse, urlunparse 
from os import path, listdir

rss = Blueprint('rss', __name__, template_folder='templates')
rss.add_app_template_global(datetime)
rss.add_app_template_global(json)


@rss.route('/')
def add_rss():
    modules = [path.splitext(f)[0] for f in listdir(path.join(path.split(__file__)[0], 'extensions'))\
               if not f.startswith('__') and path.splitext(f)[1]=='.py']
    rss_templates = []
    for m in modules:
        c = RSSHelper(m).get_class()
        rss_templates.append({
            'rss_name':c.rss_name,
            'need_args':c.needed_args,
            'optional_args':c.optional_args,
        })
    return render_template('add_rss.html', rss_templates=rss_templates)


@rss.route('/_admin/')
def admin():
    if not users.get_current_user():
        logging.debug('not users.get_current_user')
        return redirect(users.create_login_url(request.url))
    elif not users.is_current_user_admin():
        logging.debug('not users.is_current_user_admin')
        return redirect(url_for('.add_rss'))
    set_deadline()
    url_args = request.args.to_dict()
    logging.debug(u'view web: admin, args: %s' % url_args)
    if not url_args:
        return render_template('admin.html', dbs=DBRSS.query().fetch())
    elif url_args['rss_name'] and url_args['url_args']:
        rss_helper = RSSHelper(url_args['rss_name'])
        o = rss_helper.get_class()(url_args['url_args'])
        if url_args['action'] == 'update':
            o.update(manual=True)
            return redirect(url_for('.admin'))
        elif url_args['action'] == 'check_update':
            o.check_update()
            return redirect(url_for('.admin'))
        elif url_args['action'] == 'set_status' and url_args['status']:
            o.set_status(url_args['status'])
            return redirect(url_for('.admin'))
        elif url_args['action'] == 'delete':
            o.delete()
            return redirect(url_for('.admin'))
        elif url_args['action'] == 'push':
            o.push()
            return redirect(url_for('.admin'))
        elif url_args['action'] == 'reset':
            o.reset()
            return redirect(url_for('.admin'))


@rss.route('/<rss_name>')
def get_rss_from_url(rss_name):
    set_deadline()
    logging.debug(u'view web: %s, args: %s' % (rss_name, request.args.to_dict()))
    rss_helper = RSSHelper(rss_name)
    o = rss_helper.get_class()(request.args.to_dict())
    logging.debug('url: %s' % request.url)
    if o.miss_args:
        logging.debug(u'miss args: %s' % (o.miss_args))
        return render_template('miss_args.html', miss_args=o.miss_args, optional_args=o.optional_args)
    elif cmp(o.url_args.keys(), request.args.keys()):
        return redirect(url_for('.get_rss_from_url', rss_name=rss_name, **o.url_args)\
                        .replace('+', ' '))
    o.get_rss()
    return Response(render_template('rss.html', rss_obj=o), mimetype='application/xml')


@rss.route('/cron_update')
def cron_update():
    set_deadline()
    dbs=DBRSS.query(ndb.AND(DBRSS.status == RSSFlag.STATUS_ENABLED.value,
                              DBRSS.next_update_time <= datetime.now()+timedelta(hours=8))).fetch()
    for db in dbs:
        rss_helper = RSSHelper(db.rss_name)
        o = rss_helper.get_class()(db)
        o.check_update()
    return ''

@rss.route('/subscriber', methods=['GET', 'POST'])
def subscriber():
    set_deadline()
    logging.debug(str(request.args.to_dict()))
    if 'hub.challenge' in request.args.to_dict():
        logging.debug('subscribe')
        return request.args.to_dict()['hub.challenge']
    if request.method == 'POST':
        logging.debug('POST: %s, %s' % (request.form.to_dict(), request.data))
        return ''
    return ''
