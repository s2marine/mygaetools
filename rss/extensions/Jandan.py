# -*- encoding:utf-8 -*-
import sys
'lib' in sys.path or sys.path.append('lib')
'rss' in sys.path or sys.path.append('rss')
import logging

from rss_utils import RSSObject, DBRSSItem
from utils import parse_timedelta
import requests
import json
from datetime import datetime, timedelta
import re
from bs4 import BeautifulSoup

class Jandan(RSSObject):
    rss_name = 'Jandan'
    guid_is_link = False
    max_item = 50
    update_interval = parse_timedelta('2h')


    def fetch_channel(self):
        channel = self.db.channel
        channel.title = u'煎蛋热榜'
        channel.link = 'http://jandan.net/top'
        channel.description = u'煎蛋热门内容排行榜'

    def item_yield(self):
        url = 'http://jandan.net/top'
        src = requests.get(url).content
        lis = BeautifulSoup(src, 'html5lib').find('div', attrs={'id':'pic'}).find_all('li')

        offset = 0
        old_guids = [i.guid for i in self.db.items]
        for li in lis[:self.max_item]:
            pub_date = self.time_now + timedelta(seconds=offset)
            offset += 1
            title = li.find('div', attrs={'class': 'author'}).find('strong').text + ' ' + str(pub_date.strftime('%Y-%m-%d %H:%M:%d'))
            guid = li['id']
            link = li.find('div', attrs={'class': 'text'}).find('small').find('a')['href']
            if guid in old_guids:
                continue
            content = li.find('div', attrs={'class': 'text'})
            content.find('small').clear()
            content.find('span', attrs={'class': 'righttext'}).clear()
            content.find('div', attrs={'class': 'vote'}).clear()
            for img in content.find_all('img'):
                if img.name == 'img':
                    if img.has_attr('org_src'):
                        img['src'] = img['org_src']
                        del img['org_src']
                    if img.has_attr('onload'):
                        del img['onload']
            description = content.encode_contents()
            yield DBRSSItem(
                title = title,
                link = link,
                description = description,
                guid = guid,
                pub_date = pub_date
            )
