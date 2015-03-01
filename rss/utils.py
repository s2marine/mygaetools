# -*- encoding:utf-8 -*-
import sys
'lib' in sys.path or sys.path.append('lib')
import logging

import os
HostDomain = os.environ.get('HTTP_HOST')
islocal = os.environ.get('SERVER_NAME') == 'localhost'

from datetime import timedelta
import re
timedelta_re = re.compile(r'^((?P<days>\d+?)d)?((?P<hours>\d+?)h)?((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?$')
def parse_timedelta(time_str):
    if time_str == 'max':
        return timedelta().max
    elif time_str == 'min':
        return timedelta().min
    parts = timedelta_re.match(time_str)
    if not parts:
        return
    parts = parts.groupdict()
    time_params = {}
    for (name, param) in parts.items():
        if param:
            time_params[name] = int(param)
    return timedelta(**time_params)

def get_align_datetime(dt):
    minutes2add = (dt.minute//15)*15
    delta = timedelta(minutes=minutes2add) - \
            timedelta(minutes=dt.minute, seconds=dt.second, microseconds=dt.microsecond)
    return dt + delta

def set_deadline():
    from google.appengine.api import urlfetch
    urlfetch.set_default_fetch_deadline(60)
    #logging.debug('set urlfetch deadline done!')

