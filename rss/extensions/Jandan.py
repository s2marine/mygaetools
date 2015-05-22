# -*- encoding:utf-8 -*-
import sys
'lib' in sys.path or sys.path.append('lib')
'rss' in sys.path or sys.path.append('rss')
import logging

from rss_utils import RSSObject, DBRSSItem
from utils import parse_timedelta
import requests
import json
from datetime import datetime
import re
from bs4 import BeautifulSoup

class Jandan(RSSObject):
    rss_name = 'Jandan'
    guid_is_link = False
    max_item = 25
    update_interval = parse_timedelta('30m')


    def fetch_channel(self):
        channel = self.db.channel
        channel.title = u'煎蛋24小时最佳评论'
        channel.link = 'http://jandan.net/'
        channel.description = u'煎蛋24小时最佳评论'

    def item_yield(self):
        url = 'http://jandan.net/'
        src = requests.get(url).content
        authors = BeautifulSoup(src, 'html5lib').find('div', attrs={'id':'list-pic'}).find_all('div', attrs={'class':'acv_author'})
        
        old_guids = [i.guid for i in self.db.items]
        offset = 0
        for author in authors[:self.max_item]:
            title = author.text.strip().replace('\n', '').replace('\t', '')
            guid = str(int(re.search('(?<=comment-)\d+$', author.find('a')['href']).group()))
            if guid in old_guids:
                continue
            link = author.find_all('a')[1].get('href')
            tmp = BeautifulSoup().new_tag('tmp')
            for p in author.find_next('div', attrs={'class':'acv_comment'}).find_all('p'):
                for i in p:
                    if i.name == 'img':
                        if i.has_attr('org_src'):
                            i['src'] = i['org_src']
                            del i['org_src']
                        if i.has_attr('onload'):
                            del i['onload']
                    elif i.name == 'br':
                        continue
                    elif i == u'\n':
                        continue
                    tmp.contents.append(i)
            [tmp.contents.insert(i*2+1, BeautifulSoup().new_tag('br')) for i in range(len(tmp.contents))]
            description = str(tmp.encode_contents())
            pub_date = self.time_now + timedelta(seconds=offset)
            offset += 1
            yield DBRSSItem(
                title = title,
                link = link,
                description = description,
                guid = guid,
                pub_date = pub_date
            )
