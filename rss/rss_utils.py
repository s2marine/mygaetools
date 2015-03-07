# -*- encoding:utf-8 -*-
import sys
'lib' in sys.path or sys.path.append('lib')
'rss' in sys.path or sys.path.append('rss')
import logging

from google.appengine.ext import ndb
from google.appengine.api import memcache
from google.appengine.api import urlfetch

from collections import OrderedDict
from flask import url_for
import json
from utils import parse_timedelta, get_align_datetime, islocal
from datetime import timedelta, datetime, date, time
import urllib
from enum import Enum

class DBRSSChannel(ndb.Model):
    title = ndb.StringProperty(indexed=False)
    link = ndb.StringProperty(indexed=False)
    description = ndb.StringProperty(indexed=False)

class DBRSSItem(ndb.Model):
    title = ndb.StringProperty(indexed=False)
    link = ndb.StringProperty(indexed=False)
    description = ndb.TextProperty(indexed=False)
    guid = ndb.StringProperty(indexed=False)
    pub_date = ndb.DateTimeProperty(indexed=False)
    def __str__(self):
        return 'DBRSSItem(%s, %s, %s)' % (self.title, self.guid, self.pub_date)

class DBRSSUpdateStatusChunk(ndb.Model):
    no_updates = ndb.IntegerProperty(indexed=False)
    small_no_updates = ndb.IntegerProperty(indexed=False)
    failures = ndb.IntegerProperty(indexed=False)

class DBRSS(ndb.Model):
    rss_name = ndb.StringProperty(indexed=True)
    url_args = ndb.StringProperty(indexed=True)

    pre_process_args = ndb.StringProperty(indexed=False)

    update_status_chunk = ndb.LocalStructuredProperty(DBRSSUpdateStatusChunk, indexed=False)
    next_update_time = ndb.DateTimeProperty(indexed=False)
    status = ndb.StringProperty(indexed=False)

    channel = ndb.LocalStructuredProperty(DBRSSChannel, indexed=False)
    items = ndb.LocalStructuredProperty(DBRSSItem, indexed=False, repeated=True)

class RSSHelper(object):

    def __init__(self, rss_name):
        self.rss_name = rss_name
        self.rss_module = getattr(__import__('extensions.'+self.rss_name), self.rss_name)

    def get_class(self):
        return getattr(self.rss_module, self.rss_name)

class RSSException(Exception):
    pass

class RSSFlag(Enum):
    UPDATE_SUCCESS = 1
    UPDATE_NOUPDATE = 2
    UPDATE_FAILED = 3

    NEXT_UPDATE = 4
    NEXT_SMALL_UPDATE = 5
    NEXT_PAUSE = 6
    NEXT_FAILED = 7

    STATUS_ENABLED = 'Enabled'
    STATUS_DISABLED = 'Disabled'
    STATUS_PAUSED = 'Paused'

    REASON_RSSPAUSED = 'a rss has paused'

class RSSObject(object):

    def __str__(self):
        return '%s(url_args:%s)' % (self.rss_name, self.url_args)

    rss_name = ''
    guid_is_link = True
    max_item = 10
    needed_args = {
    }
    optional_args = {
    }

    update_interval = parse_timedelta('1d')
    no_update_limit = float('inf')
    small_update_interval = parse_timedelta('0s')
    small_no_update_limit = 0
    check_failed_interval = lambda self,x: x*parse_timedelta('15m')
    failures_limit = 10

    def __init__(self, args):
        # args==url_args
        if isinstance(args, dict):
            args = args
        # args==url_args_str
        elif isinstance(args, basestring):
            args = json.loads(args)
        # from check update
        elif isinstance(args, ndb.Model):
            self.db = args
            args = json.loads(self.db.url_args)
        self.filter_args(args)
        self.init_db()


    def filter_args(self, args):
        self.url_args = OrderedDict()
        self.miss_args = self.needed_args.copy()
        for k in self.needed_args.keys():
            if k in args:
                self.url_args[k] = args[k]
                del self.miss_args[k]
        for k in self.optional_args.keys():
            if k in args:
                self.url_args[k] = args[k]
        self.url_args_str = json.dumps(self.url_args, ensure_ascii=False)

    def init_db(self):
        self.db = self.get_from_mem()
        if not self.db:
            self.db = self.get_from_db()
            if self.db:
                self.add_into_mem()
        if not self.db:
            self.db = DBRSS(
                rss_name=self.rss_name,
                url_args=self.url_args_str,
                update_status_chunk=DBRSSUpdateStatusChunk(),
                status=RSSFlag.STATUS_ENABLED.value,
                channel=DBRSSChannel(),
                items=[]
            )


    def check_pre_process(self):
        if self.db.pre_process_args:
            self.pre_process_args = json.loads(self.db.pre_process_args)
        else:
            self.pre_process()
        self.apply_pre_process()

    def pre_process(self):
        self.pre_process_args = {}
        self.pre_process_args.update(self.url_args)
        self.pre_process_args.update(self.get_pre_process_args())
        self.db.pre_process_args = json.dumps(self.pre_process_args, ensure_ascii=False)

    def get_pre_process_args(self):
        return {}

    def apply_pre_process(self):
        pass


    def check_channel(self):
        if not self.db.channel.link:
            self.fetch_channel()

    def fetch_channel(self):
        pass


    def check_items(self):
        if not self.db.items:
            return self.fetch_items()

    def fetch_items(self):
        try:
            update_result = RSSFlag.UPDATE_NOUPDATE
            for i in self.item_yield():
                self.db.items.append(i)
                logging.debug('rss add item %s' % i)
                update_result = RSSFlag.UPDATE_SUCCESS
            self.db.items = sorted(self.db.items, key=lambda x:x.pub_date, reverse=True)
            del self.db.items[self.max_item:]
        except:
            update_result = RSSFlag.UPDATE_FAILED
            logging.exception('fetch items failed!')
        return update_result


    def deal_update_status(self, update_result):
        chunk = self.db.update_status_chunk
        if update_result == RSSFlag.UPDATE_SUCCESS:
            chunk.no_updates = 0
            chunk.small_no_updates = 0
            chunk.failures = 0
            next_update_type = RSSFlag.NEXT_UPDATE
        elif update_result == RSSFlag.UPDATE_NOUPDATE:
            chunk.failures = 0
            if chunk.small_no_updates < self.small_no_update_limit:
                chunk.small_no_updates += 1
                next_update_type = RSSFlag.NEXT_SMALL_UPDATE
            elif chunk.no_updates < self.no_update_limit:
                chunk.small_no_updates = 0
                chunk.no_updates += 1
                next_update_type = RSSFlag.NEXT_UPDATE
            else:
                next_update_type = RSSFlag.NEXT_PAUSE
        elif update_result == RSSFlag.UPDATE_FAILED:
            if chunk.failures < self.failures_limit:
                chunk.failures += 1
                next_update_type = RSSFlag.NEXT_FAILED
            else:
                next_update_type = RSSFlag.NEXT_PAUSE
        logging.debug('update_result, next_update_type: %s, %s' % (update_result, next_update_type))
        return next_update_type

    def setup_next_update(self, update_type):
        last_update = self.get_last_update_time()
        if update_type == RSSFlag.NEXT_UPDATE:
            if isinstance(self.update_interval, timedelta):
                next_update_time = last_update
                while next_update_time < self.time_now:
                    next_update_time += self.update_interval
            elif isinstance(self.update_interval, list):
                today = date.today()
                today_time = datetime.combine(today, time())
                delta = None
                for _d in self.update_interval:
                    if today_time+_d > self.time_now:
                        delta = _d
                        break
                if delta:
                    next_update_time = today_time + delta
                else:
                    next_update_time = today_time + timedelta(days=1) + self.update_interval[0]
        elif update_type == RSSFlag.NEXT_SMALL_UPDATE:
            next_update_time = self.time_now + self.small_update_interval
        elif update_type == RSSFlag.NEXT_FAILED:
            db.next_update_time = self.time_now + \
                    self.check_failed_interval(self.db.update_status_chunk.failures)
        elif update_type == RSSFlag.NEXT_PAUSE:
            self.db.status = RSSFlag.STATUS_PAUSED.value
            self.mail(RSSFlag.REASON_RSSPAUSED)
        if update_type != RSSFlag.NEXT_PAUSE:
            self.db.next_update_time = get_align_datetime(next_update_time)

    def get_last_update_time(self):
        return self.time_now

    
    def get_from_db(self):
        return DBRSS.query(DBRSS.rss_name==self.rss_name,
                           DBRSS.url_args==self.url_args_str).get()

    def add_into_mem(self):
        return memcache.set(self.rss_name+':'+self.url_args_str, self.db)

    def get_from_mem(self):
        return memcache.get(self.rss_name+':'+self.url_args_str)

    def clean_mem(self):
        return memcache.delete(self.rss_name+':'+self.url_args_str)

    def istime(self):
        logging.debug('istime check: %s next: %s, now: %s' % (self.rss_name, self.db.next_update_time, self.time_now))
        return self.db.next_update_time <= self.time_now

    @property
    def time_now(self):
        return datetime.now()+timedelta(hours=8)

    def mail(self, reason):
        pass

    def push(self):
        if islocal:
            return
        hub_url = url_for('rss.get_rss_from_url', rss_name=self.rss_name, _external=True, **self.url_args)
        push_url = 'https://pubsubhubbub.appspot.com/'
        data = urllib.urlencode({
            'hub.url': hub_url,
            'hub.mode': 'publish'})
        response = urlfetch.fetch(push_url, data, urlfetch.POST)
        logging.debug('push %s: %s, response %s' % (self.rss_name, hub_url, response.status_code))

    def get_rss(self):
        self.check_pre_process()
        self.check_channel()
        update_result = self.check_items()
        if update_result == RSSFlag.UPDATE_SUCCESS:
            next_update_type = self.deal_update_status(update_result)
            self.setup_next_update(next_update_type)
            self.db.put()
            self.add_into_mem()
        elif update_result == RSSFlag.UPDATE_FAILED:
            raise RSSException('Get rss failed in first time.')

    def set_status(self, status):
        self.db.status = status
        self.db.put()
        self.add_into_mem()

    def delete(self):
        if self.db.key:
            self.db.key.delete()
            self.clean_mem()

    def check_update(self):
        if self.istime():
            self.update()

    def update(self, manual=False):
        self.check_pre_process()
        self.check_channel()
        update_result = self.fetch_items()
        if not manual or update_result == RSSFlag.UPDATE_SUCCESS:
            next_update_type = self.deal_update_status(update_result)
            self.setup_next_update(next_update_type)
            self.db.put()
            self.add_into_mem()
        if update_result == RSSFlag.UPDATE_SUCCESS:
            self.push()
