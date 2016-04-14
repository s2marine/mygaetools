# -*- encoding:utf-8 -*-
import sys
'lib' in sys.path or sys.path.append('lib')
'rss' in sys.path or sys.path.append('rss')
import logging

import config

from rss_utils import RSSObject, DBRSSItem
from utils import parse_timedelta
import requests
from datetime import datetime, timedelta
import time

class Bilibili(RSSObject):
    rss_name = 'Bilibili'
    guid_is_link = False
    update_interval = [parse_timedelta('7h15m'), ]
    appkey = config.bilibili_appkey
    headers = config.bilibili_headers

    def fetch_channel(self):
        channel = self.db.channel
        channel.title = 'Bilibili'
        channel.link = 'http://www.bilibili.com/'
        channel.description = u'嗶哩嗶哩 - ( ゜- ゜)つロ 乾杯~'

    def item_yield(self):
        hot_list_url = 'http://api.bilibili.com/list?type=json&appkey=%(appkey)s&days=1&order=hot&original=true&pagesize=%(pagesize)s'\
                % {'appkey':self.appkey, 'pagesize':self.max_item}
        video_detail_url = 'http://api.bilibili.com/view?id=%(id)s&appkey=%(appkey)s&type=json'

        hot_list = requests.get(hot_list_url).json()['list']

        old_guids = [i.guid for i in self.db.items]
        for i in range(self.max_item):
            time.sleep(1)
            i = str(i)
            guid = aid = str(hot_list[i]['aid'])
            if guid in old_guids:
                continue
            link = 'http://www.bilibili.com/video/av'+aid+'/'

            url = video_detail_url % {'appkey':self.appkey, 'id':aid}
            video_detail = requests.get(url, headers=self.headers).json()
            title = video_detail['title']
            description = '<img src="'+video_detail['pic']+'"/><br/>'+video_detail['description']
            pub_date = datetime.fromtimestamp(video_detail['created'])+timedelta(hours=8)

            yield DBRSSItem(
                title = title,
                link = link,
                description = description,
                guid = guid,
                pub_date = pub_date
            )
