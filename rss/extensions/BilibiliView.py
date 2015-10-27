# -*- encoding:utf-8 -*-
import sys
'lib' in sys.path or sys.path.append('lib')
'rss' in sys.path or sys.path.append('rss')
import logging

import config

from rss_utils import RSSObject, DBRSSItem
import requests
from datetime import datetime, timedelta
import re


class BilibiliView(RSSObject):
    rss_name = 'BilibiliView'
    guid_is_link = True
    needed_args = {
        'url': 'which view you wanna fetch',
    }
    appkey = config.bilibili_appkey
    headers = config.bilibili_headers

    def get_pre_process_args(self):
        aid = int(re.search('\d+', self.pre_process_args['url']).group())
        return {'aid': aid}

    def fetch_channel(self):
        channel = self.db.channel
        pre_process_args = self.pre_process_args
        view_url = 'http://api.bilibili.com/view?id=%(aid)s&appkey=%(appkey)s&type=json' \
                % {'aid':pre_process_args['aid'], 'appkey': self.appkey, 'type':'json'}
        j = requests.get(view_url).json()
        channel.title = j['title']
        channel.link = pre_process_args['url']
        channel.description = ''

    def item_yield(self):
        pre_process_args = self.pre_process_args
        video_list_url = 'http://api.bilibili.com/view?id=%(aid)s&appkey=%(appkey)s&type=json&page=1' \
                % {'aid':pre_process_args['aid'], 'appkey':self.appkey}
        video_detail_url = 'http://api.bilibili.com/view?id=%(aid)s&appkey=%(appkey)s&type=json&page=%(pages)s'

        video_count = requests.get(video_list_url).json()['pages']
        
        old_guids = [i.guid for i in self.db.items]
        for i in range(video_count, max(video_count-self.max_item, 0), -1):
            guid = 'http://www.bilibili.com/video/av%(aid)s/index_%(pages)s.html' \
                    % {'aid':pre_process_args['aid'], 'pages': i}

            if guid in old_guids:
                continue
            link = guid

            url = video_detail_url % {'aid':pre_process_args['aid'], 'appkey':self.appkey, 'pages': i}
            video_detail = requests.get(url, headers=self.headers).json()
            title = video_detail['partname']
            description = '<img src="'+video_detail['pic']+'"/><br/>'+video_detail['description']
            pub_date = self.time_now

            yield DBRSSItem(
                title = title,
                link = link,
                description = description,
                guid = guid,
                pub_date = pub_date
            )
