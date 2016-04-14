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
import time

class BilibiliSpace(RSSObject):
    rss_name = 'BilibiliSpace'
    guid_is_link = False
    needed_args = {
        'url': 'which space you wanna fetch',
    }
    appkey = config.bilibili_appkey
    headers = config.bilibili_headers

    def get_pre_process_args(self):
        mid = int(re.search('\d+$', self.pre_process_args['url']).group())
        return {'mid': mid}

    def fetch_channel(self):
        channel = self.db.channel
        pre_process_args = self.pre_process_args
        channel_url = 'http://api.bilibili.com/userinfo?mid=%(mid)s&type=%(type)s' \
                % {'mid':pre_process_args['mid'], 'type':'json'}
        j = requests.get(channel_url).json()
        channel.title = j['name']
        channel.link = pre_process_args['url']
        channel.description = j['name']+u'的空间'

    def item_yield(self):
        pre_process_args = self.pre_process_args
        video_list_url = 'http://api.bilibili.com/list?type=json&mid=%(mid)s&appkey=%(appkey)s&pagesize=%(pagesize)s' \
                % {'mid':pre_process_args['mid'], 'appkey':self.appkey, 'pagesize':self.max_item}
        video_detail_url = 'http://api.bilibili.com/view?id=%(id)s&appkey=%(appkey)s&type=json'

        video_list = requests.get(video_list_url).json()['list']

        old_guids = [i.guid for i in self.db.items]
        for i in range(min(self.max_item, int(video_list['num']))):
            time.sleep(1)
            i = str(i)
            guid = aid = str(video_list[i]['aid'])
            if guid in old_guids:
                continue
            link = 'http://www.bilibili.com/video/av'+aid+'/'

            url = video_detail_url % {'id':aid, 'appkey':self.appkey}
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
