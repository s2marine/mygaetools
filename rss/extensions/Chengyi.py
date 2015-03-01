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

class Chengyi(RSSObject):
    rss_name = 'Chengyi'
    update_interval = parse_timedelta('1h')
    needed_args = {
    }
    max_item = 25

    def fetch_channel(self):
        channel = self.db.channel
        channel.title = u'诚毅通知集合'
        channel.link = 'http://cyrj.tk'
        channel.description = u'诚毅学院各个网站通知集合'

    def item_yield(self):
        sites = [self.site1_items(), self.site2_items(), self.site3_items(), self.site4_items()]
        old_guids = [i.guid for i in self.db.items]
        for i in range(self.max_item):
            mod = i % len(sites)
            l = i // len(sites)
            if sites[mod] and l < len(sites[mod]): 
                if sites[mod][l].guid not in old_guids:
                    yield sites[mod][l]

    #教务部
    def site1_items(self):
        result = []
        url = 'http://cyjwb.jmu.edu.cn/lists.asp?lbm=%CD%A8%D6%AA%B9%AB%B8%E6'
        soup = BeautifulSoup(requests.get(url).content)
        table = soup.findAll('table')[2]
        p = re.compile(u'\d+-\d+-\d+ \d+:\d+:\d+')
        for i in table.findAll('a')[:-3]: #去掉最后的翻页
            title = i.text.strip()
            link = 'http://cyjwb.jmu.edu.cn/'+i.get('href')
            description = ''
            guid = link
            pub_date_str = p.search(i.next_sibling.next_sibling.text).group()
            pub_date = datetime.strptime(pub_date_str, '%Y-%m-%d %H:%M:%S')
            result.append(DBRSSItem(
                title = title,
                link = link,
                description = description,
                guid = guid,
                pub_date = pub_date
            ))
        return result
    
    #考试安排
    def site2_items(self):
        result = []
        url = 'http://cyjwb.jmu.edu.cn/lists.asp?lbm=%BF%BC%CA%D4%B0%B2%C5%C5'
        soup = BeautifulSoup(requests.get(url).content)
        table = soup.findAll('table')[2]
        p = re.compile(u'\d+-\d+-\d+ \d+:\d+:\d+')
        for i in table.findAll('a')[:-3]: #去掉最后的翻页
            title = i.text.strip()
            link = 'http://cyjwb.jmu.edu.cn/'+i.get('href')
            description = ''
            guid = link
            pub_date_str = p.search(i.next_sibling.next_sibling.text).group()
            pub_date = datetime.strptime(pub_date_str, '%Y-%m-%d %H:%M:%S')
            result.append(DBRSSItem(
                title = title,
                link = link,
                description = description,
                guid = guid,
                pub_date = pub_date
            ))
        return result

    #诚毅学院
    def site3_items(self):
        result = []
        url = u'http://chengyi.jmu.edu.cn/s/206/t/1129/p/1/c/4737/d/4752/list.htm'
        soup = BeautifulSoup(requests.get(url).content)
        table = soup.find('div', attrs={'id':'newslist'}).find('table')
        for stable in table.findAll('table'):
            title = stable.a.text.strip()
            link = 'http://chengyi.jmu.edu.cn/'+stable.a.get('href')
            description = ''
            guid = link
            pub_date_str = stable.findAll('td')[1].text
            pub_date = datetime.strptime(pub_date_str, '%Y-%m-%d')
            result.append(DBRSSItem(
                title = title,
                link = link,
                description = description,
                guid = guid,
                pub_date = pub_date
            ))
        return result

    #体育教研部
    def site4_items(self):
        result = []
        url = u'http://cytyjys.jmu.edu.cn/s/221/t/1190/p/12/list.htm'
        soup = BeautifulSoup(requests.get(url).content)
        tables = soup.findAll('table', attrs={'class':'columnStyle'})
        for i in tables:
            title = i.find('font').text
            link = 'http://cytyjys.jmu.edu.cn'+i.find('a')['href']
            description = ''
            guid = link
            pub_date = self.time_now
            result.append(DBRSSItem(
                title = title,
                link = link,
                description = description,
                guid = guid,
                pub_date = pub_date
            ))
        return result
