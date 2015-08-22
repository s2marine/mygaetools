# -*- encoding:utf-8 -*-
import sys
'lib' in sys.path or sys.path.append('lib')
'rss' in sys.path or sys.path.append('rss')
import logging

import config

from rss_utils import RSSObject, DBRSSItem
from utils import parse_timedelta
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re

class BilibiliSP(RSSObject):
    rss_name = 'BilibiliSP'
    guid_is_link = False
    needed_args = {
        'url': 'which sp you wanna fetch',
    }
    optional_args = {
        'isbangumi': '0 or 1',
    }
    appkey = config.bilibili_appkey
    headers = config.bilibili_headers

    def get_pre_process_args(self):
        result = {}
        if '/sp/' in self.pre_process_args['url']:
            src = requests.get(self.pre_process_args['url']).content
            result['spid'] = re.search('var spid ?= ?"(\d+?)"', src).group(1)
            if 'isbangumi' not in self.pre_process_args:
                result['isbangumi'] = int(re.search('var isbangumi ?= ?"(\d+?)"', src).group(1))
        elif '/bangumi/' in self.pre_process_args['url']:
            src = requests.get(self.pre_process_args['url']).content
            href = BeautifulSoup(src).find('div', {'id':'episode_list'}).find('a').['href']
            aid = re.search('\d+', a.get('href')).group(0)
            video_detail_url = 'http://api.bilibili.com/view?id=%(id)s&appkey=%(appkey)s&type=json'
            url = video_detail_url % {'id':aid, 'appkey':self.appkey}
            video_detail = requests.get(url, headers=self.headers).json()
            result['spid'] = video_detail['spid']
            result['isbangumi'] = 1 if 'bangumi' in video_detail else 0
        return result

    def apply_pre_process(self):
        if self.pre_process_args['isbangumi']:
            self.update_interval = parse_timedelta('7d')
            self.no_update_limit = 2
            self.small_update_interval = parse_timedelta('30m')
            self.small_no_update_limit = 24*2

    def fetch_channel(self):
        channel = self.db.channel
        pre_process_args = self.pre_process_args
        channel_url = 'http://api.bilibili.com/sp?type=json&spid=%(spid)s' \
                % {'spid':pre_process_args['spid']}
        j = requests.get(channel_url).json()
        channel.title = j['title']
        channel.link = pre_process_args['url']
        channel.description = j['description']

    def item_yield(self):
        pre_process_args = self.pre_process_args
        video_list_url = 'http://api.bilibili.com/spview?spid=%(spid)s&type=json&bangumi=%(isbangumi)s' \
                % {'spid':pre_process_args['spid'], 'isbangumi':pre_process_args['isbangumi']}
        video_detail_url = 'http://api.bilibili.com/view?id=%(id)s&appkey=%(appkey)s&type=json'

        video_list = requests.get(video_list_url).json()['list']
        
        old_guids = [i.guid for i in self.db.items]
        for i in video_list[:self.max_item]:
            guid = aid = str(i['aid'])
            if guid in old_guids:
                continue
            link = 'http://www.bilibili.com/video/av'+aid+'/'
            
            url = video_detail_url % {'id':i['aid'], 'appkey':self.appkey}
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

    def get_last_update_time(self):
        if self.pre_process_args['isbangumi']:
            logging.debug('last item: %s, %s' % (self.db.items[0].title, self.db.items[0].pub_date))
            return self.db.items[0].pub_date
        else:
            return self.time_now
