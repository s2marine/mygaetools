# -*- encoding:utf-8 -*-
import sys
'lib' in sys.path or sys.path.append('lib')
'rss' in sys.path or sys.path.append('rss')
import logging

import config

from rss_utils import RSSObject, DBRSSItem
import requests
import re
from datetime import datetime, timedelta
import base64
from Crypto.Cipher import AES
import urllib
from bs4 import BeautifulSoup
import json
import lxml.html, lxml.etree

class WeiXin(RSSObject):
    rss_name = 'Weixin'
    guid_is_link = False
    needed_args = {
        'openid': 'which person you wanna fetch',
    }


    def get_pre_process_args(self):
        def get_eqs(openid):
            def _to_bytes(text):
                if isinstance(text, bytes):
                    return text
                return text.encode('utf-8')
            def _to_unicode(text):
                if isinstance(text, str):
                    return text
                return text.decode('utf-8')
            key = '8d03ae022be'
            sogou = 'sogou'
            IV = '0000000000000000'
            i = key+sogou
            o = openid+'hdq='+sogou
            length = 16 - (len(o) % 16)
            o += chr(length) * length
            e = AES.new(_to_bytes(i), AES.MODE_CBC, IV)
            data = _to_unicode(base64.b64encode(e.encrypt(o)))

            h = ''
            l = 0
            for m in range(len(data)):
                h += data[m]
                if (m == pow(2, l)) and l < len(sogou):
                    h += sogou[l]
                    l += 1
            return urllib.quote(h)
        return {'eqs': get_eqs(self.pre_process_args['openid'])}

    def fetch_channel(self):
        channel = self.db.channel
        pre_process_args = self.pre_process_args
        channel_url = 'http://weixin.sogou.com/gzh?openid=%(openid)s' \
                % {'openid':self.pre_process_args['openid']}
        s = BeautifulSoup(requests.get(channel_url).text, 'html5lib')
        channel.title = s.find('h3', {'id': 'weixinname'}).text
        channel.link = channel_url
        channel.description = s.find('span', {'class': 'sp-txt'}).text

    def item_yield(self):
        pre_process_args = self.pre_process_args
        post_list = 'http://weixin.sogou.com/gzhjs?cb=sogou.weixin.gzhcb&openid=%(openid)s&eqs=%(eqs)s&ekv=3' \
                % {'openid':pre_process_args['openid'], 'eqs':pre_process_args['eqs']}

        r = requests.get(post_list).text
        posts = json.loads(r[r.find('{'):r.rfind('}')+1])['items']

        old_guids = [i.guid for i in self.db.items]
        for post in posts:
            root = lxml.etree.fromstring(post.replace(u'encoding="gbk"', ''))
            guid = root.xpath('//docid/text()')[0]
            if guid in old_guids:
                continue
            title = root.xpath('//title/text()')[0]
            link = root.xpath('//url/text()')[0]
            pub_date = datetime.fromtimestamp(int(root.xpath('//lastModified/text()')[0]))+timedelta(hours=8)
            description = self.get_post_content(link)

            yield DBRSSItem(
                title = title,
                link = link,
                description = description,
                guid = guid,
                pub_date = pub_date
            )

    def get_post_content(self, url):
        html = requests.get(url).text
        root = lxml.html.fromstring(html)

        # 抽取封面cover图片
        _COVER_RE = re.compile(r'cover = "(http://.+)";')
        script = root.xpath('//*[@id="media"]/script/text()')
        cover = None
        if script:
            l = _COVER_RE.findall(script[0])
            if l:
                cover = l[0]

        # 抽取文章内容
        try:
            content = root.xpath('//*[@id="js_content"]')[0]
        except IndexError:
            return ''

        # 处理图片链接
        for img in content.xpath('.//img'):
            if not 'src' in img.attrib:
                img.attrib['src'] = img.attrib.get('data-src', '')

        # 生成封面
        if cover:
            coverelement = lxml.etree.Element('img')
            coverelement.set('src', cover)
            content.insert(0, coverelement)

        return lxml.html.tostring(content, encoding='unicode')
