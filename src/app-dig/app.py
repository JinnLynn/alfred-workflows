#!/usr/bin/env python
# -*- coding: utf-8 -*-
#! 强制默认编码为utf-8
import sys
reload(sys)
sys.setdefaultencoding('utf8')

import os, urllib, urllib2, re, hashlib, subprocess, datetime
try:
    import xml.etree.cElementTree as et
except ImportError:
    import xml.etree.ElementTree as et

import alfred
from bs4 import BeautifulSoup

from pprint import pprint

CACHE_EXPIRE = 60 * 30

__version__ = '1.0'

default_feeds = [
    {
        'title' : 'Apps Going Free for Mac',
        'feed'  : 'http://appshopper.com/feed/paidtofree/?platform=mac',
        'cmd'   : 'apps-going-free-for-mac'
    },
    {
        'title' : 'Apps Going Free for iPhone',
        'feed'  : 'http://appshopper.com/feed/paidtofree/?device=iPhone',
        'cmd'   : 'apps-going-free-for-iphone'
    },
    {
        'title' : 'Apps Going Free for iPad',
        'feed'  : 'http://appshopper.com/feed/paidtofree/?device=iPad',
        'cmd'   : 'apps-going-free-for-ipad'
    },
]

more_apps_feed = [
    {
        'title' : 'Popular Changes for {title}',
        'feed'  : 'http://appshopper.com/feed/?{type}&mode=featured',
    },
    {
        'title' : 'Popular New Apps (Free) for {title}',
        'feed'  : 'http://appshopper.com/feed/?{type}&mode=featured&filter=new&type=free',
    },
    {
        'title' : 'Popular New Apps (Paid) for {title}',
        'feed'  : 'http://appshopper.com/feed/?{type}&mode=featured&filter=new&type=paid',
    },
    {
        'title' : 'Popular Updates for {title}',
        'feed'  : 'http://appshopper.com/feed/?{type}&mode=featured&filter=updates',
    },
    {
        'title' : 'Popular Price Drops for {title}',
        'feed'  : 'http://appshopper.com/feed/?{type}&mode=featured&filter=price',
    },
    {
        'title' : 'All Changes for {title}',
        'feed'  : 'http://appshopper.com/feed/?{type}',
    },
    {
        'title' : 'All New Apps  for {title}',
        'feed'  : 'http://appshopper.com/feed/?{type}&filter=new',
    },
    {
        'title' : 'All New Apps (Free) for {title}',
        'feed'  : 'http://appshopper.com/feed/?{type}&filter=new&type=free',
    },
    {
        'title' : 'All Updates for {title}',
        'feed'  : 'http://appshopper.com/feed/?{type}&filter=new&type=paid',
    },
    {
        'title' : 'All Updates for {title}',
        'feed'  : 'http://appshopper.com/feed/?{type}&filter=updates',
    },
    {
        'title' : 'All Price Drops for {title}',
        'feed'  : 'http://appshopper.com/feed/?{type}&filter=price',
    }
]

more_apps_types = {
            'mac'   : {'title':'Mac','type':'platform=mac'},
            'ipad'  : {'title':'iPad','type':'device=ipad'},
            'iphone': {'title':'iPhone','type':'device=iphone'}
        }

class App(object):
    def __init__(self):
        self.enable_appiconshow = alfred.config.get('app_icon_show', True)

    def run(self):
        cmd = alfred.argv(1)
        if not cmd:
            return self.showDefaultList()
        cmd = cmd.lower()
        for feed in default_feeds:
            if cmd == feed['cmd']:
                self.showAppsFromFeed(feed['feed'])

        self.tryShowMoreApps()

        if cmd.startswith('search'):
            cmd = 'search'
        if cmd.startswith('more-apps-'):
            cmd = 'more-apps'

        cmd_map = {
            'search'    : lambda: self.search(),
            'wish'      : lambda: self.showWishList(),
            'setting'   : lambda: self.showSettings(),
            'more-apps' : lambda: self.showMoreApps()
        }
        if cmd in cmd_map.keys():
            return cmd_map[cmd]()
        return self.showDefaultList()

    def openUrl(self, url):
        opener = urllib2.build_opener()
        opener.addheaders.append(('Cookie', 'AS_country=US; expires=Thu, 12 Dec 2030 00:00:00 ; path=/'))
        return opener.open(url).read()

    def fetchDataFromFeed(self, feed, cached=True):
        data = alfred.cache.get(feed)
        if cached and data: 
            return True, data
        try:
            # res = urllib2.urlopen(feed).read()
            rss = self.openUrl(feed)
            rss_tree = et.fromstring(rss)
        except Exception, e:
            return False, e.message
        data = []
        for item in rss_tree.iterfind('channel/item'):
            try:
                app_link = item.find('link').text.strip()
                desc = item.find('description').text.strip()
                soup = BeautifulSoup(desc)
                app_icon = soup.find('img').attrs.get('src', '')
                itunes = soup.find('a')
                app_store_link = itunes.attrs.get('href', '').lstrip('/')
                app_store_link = os.path.join('http://appshopper.com/', app_store_link)
                # 清除掉该链接节点
                itunes.clear()
                lines = soup.text.strip().splitlines()
                app_name = lines[0]
                desclines = reversed([s.strip('() ') for s in lines[1:4]])
                app_desc = ', '.join(desclines)            
            except:
                continue
            data.append({
                'link'      : app_link,
                'icon'      : app_icon,
                'name'      : app_name,
                'desc'      : app_desc,
                'store'     : app_store_link,
                'category'  : ''
                })
        if data:
            if cached:
                alfred.cache.set(feed, data, CACHE_EXPIRE)
            return True, data
        return False, 'Nothing found.'

    def fetchDataFromePage(self, page, cached=True):
        data = alfred.cache.get(page)
        if cached and data:
            return True, data
        try:
            content = self.openUrl(page)
            match = re.search(r'<div class="content">(.*)</div><!-- content -->', content, flags=re.DOTALL)
            if not match:
                return False, 'parse search page failed.'
            soup = BeautifulSoup(match.group(1))
        except Exception, e:
            return False, e.message

        data = []
        for item in soup.find_all('li', id=True):
            try:
                if not item['id'].startswith('app_'):
                    continue
                title_tag = item.select('h3.hovertip')[0]
                app_name = title_tag.string.strip()
                price_tag = item.select('.price')[0]
                app_store_link = os.path.join('http://appshopper.com', price_tag.find('a').attrs.get('href', '').lstrip('/'))
                price_tag.find('a').extract()
                app_price = price_tag.select('.misc')[0].get_text()
                if not app_price:
                    app_cents = price_tag.select('.cents')[0].get_text()
                    if app_cents:
                        app_cents = '.{}'.format(app_cents)
                    price_tag.find('span').extract()
                    price_tag.find('span').extract()
                    app_price = price_tag.get_text()
                    app_price = '{}{}'.format(app_price, app_cents)
                app_category = item.select('.category')[0].string.strip()
                app_version = item.find_all('dd')[2].string.strip()
                app_device = item.select('dl > dt > nobr')[0].string.strip()

                icon_tag = item.find('img')
                app_icon = icon_tag['src'].strip()
                app_link = icon_tag.find_parent('a')['href'].strip()
            except Exception, e:
                continue
            data.append({
                'name'      : app_name,
                'link'      : app_link,
                'desc'      : 'Price: {:6}  Version: {}  Category: {}  Device: {}'.format(app_price, app_version, app_device, app_category),
                'icon'      : app_icon,
                'store'     : app_store_link,
                'category'  : app_category
                })
        return True, data

    def downloadAppIcon(self, data):
        if not self.enable_appiconshow:
            return
        links = []
        for item in data:
            img_url = item['icon']
            if not img_url or self.getLocalAppIcon(img_url):
                continue
            links.append(img_url)
        if links:
            subprocess.check_output(['python', 'action.py', 'download', ','.join(links)])

    def getLocalAppIcon(selg, img_url):
        storage_path = os.path.join('/tmp', alfred.bundleID())
        _, ext = os.path.splitext(img_url)
        if not ext:
            return
        filename = '{}{}'.format( hashlib.md5(img_url).hexdigest(), ext )
        filepath = os.path.join(storage_path, filename)
        if os.path.exists(filepath):
            return filepath

    def outputFeedback(self, success, data, no_found_msg=''):
        if not success or not data:
            alfred.exitWithFeedback(
                title       = 'No App Found',
                subtitle    = no_found_msg
                )
        self.downloadAppIcon(data)
        feedback = alfred.Feedback()
        for app in data:
            icon = ''
            if self.enable_appiconshow:
                icon = self.getLocalAppIcon(app['icon'])
            feedback.addItem(
                title       = app['name'],
                subtitle    = app['desc'],
                arg         = 'open-link {}'.format(app['store']),
                icon        = icon if icon else ''
                )
        feedback.output()

    def showDefaultList(self):
        feedback = alfred.Feedback()
        if alfred.argv(1):
            feedback.addItem(
                title           = 'Command No Found.'
                )
        feedback.addItem(
            title               = 'Apps Search',
            subtitle            = 'search apps in AppShopper',
            autocomplete        = 'search ',
            valid               = False
            )
        if alfred.config.get('username'):
            feedback.addItem(
                title           = 'Apps Wish List',
                subtitle        = '{}\'s Wish list in AppShopper'.format(alfred.config.get('username')),
                autocomplete    = 'wish',
                valid           = False
                )
        for item in default_feeds:
            feedback.addItem(
                title           = item['title'],
                autocomplete    = item['cmd'],
                valid           = False
                )
        feedback.addItem(
            title               = 'More Apps for Mac',
            subtitle            = '',
            autocomplete        = 'more-apps-mac',
            valid               = False
            )
        feedback.addItem(
            title               = 'More Apps for iPhone',
            subtitle            = '',
            autocomplete        = 'more-apps-iphone',
            valid               = False
            )
        feedback.addItem(
            title               = 'More Apps for iPad',
            subtitle            = '',
            autocomplete        = 'more-apps-ipad',
            valid               = False
            )

        # 设置入口
        feedback.addItem(
            title               = 'Apps Settings',
            subtitle            = 'set AppShopper username, clear cache ...',
            autocomplete        = 'setting',
            valid               = False
            )
        feedback.output()

    def showAppsFromFeed(self, feed):
        success, data = self.fetchDataFromFeed(feed)
        return self.outputFeedback(success, data)

    def search(self):
        query = []
        argv_pos = 2
        while True:
            arg = alfred.argv(argv_pos)
            if not arg:
                break
            query.append(arg)
            argv_pos += 1
        query = ' '.join(query)
        if not query:
            alfred.exitWithFeedback(
                title = 'Search for apps in AppShopper'
                )
        query = urllib.urlencode({'search' : query})
        url = 'http://appshopper.com/search/??cat=&platform=all&device=all&sort=rel&dir=asc&{}'.format(query)
        success, data = self.fetchDataFromePage(url, False)
        return self.outputFeedback(success, data)

    def showWishList(self):
        username = alfred.config.get('username')
        if not username:
            alfred.exitWithFeedback(
                title           = 'AppShopper Username Is Missing.',
                subtitle        = 'you MUST set your AppShopper username and share it in AppShopper account setting if you want to see wish list.',
                autocomplete    = 'setting username',
                valid           = False
                )
        wish_feed = 'http://appshopper.com/feed/user/{}/wishlist'.format(username)
        success, data = self.fetchDataFromFeed(wish_feed, False)
        no_found_msg = 'maybe you don\'t share your wifh list, you need to check "Share My Wishlist" in AppShopper Wish List page'
        self.outputFeedback(success, data, no_found_msg)

    def showSettings(self):
        sub = alfred.argv(2)
        if sub == 'username':
            usr = alfred.argv(3) if alfred.argv(3) else ''
            old_usr = alfred.config.get('username') if alfred.config.get('username') else ''
            alfred.exitWithFeedback(
                title       = 'Set AppShopper username',
                subtitle    = 'new uername is {}, current: {}'.format(usr, old_usr),
                arg         = 'set-username {}'.format(usr)
                )
        feedback = alfred.Feedback()
        feedback.addItem(
            title           = 'Set AppShopper Username',
            subtitle        = 'you MUST config this if you want to see your wish list.',
            autocomplete    = 'setting username ',
            valid           = False
            )
        feedback.addItem(
            title           = 'Clean',
            subtitle        = 'clear all cache',
            arg             = 'clean'
            )
        title = '{} App Icon Showing'.format('Enable' if not self.enable_appiconshow else 'Disable')
        feedback.addItem(
            title           = title,
            subtitle        = 'enable may take more time to fetch data.',
            arg             = 'app-icon-showing {}'.format('enable' if not self.enable_appiconshow else 'disable')
            )
        feedback.output()

    def showMoreApps(self):
        sub = alfred.argv(1)
        t = sub[10:].lower()
        if t not in more_apps_types.keys():
            self.exitWithFeedback(
                title = 'Nothing found'
                )
        feedback = alfred.Feedback()
        for item in more_apps_feed:
            title = item['title'].format(**more_apps_types[t])
            cmd = '-'.join(title.lower().split(' '))
            feedback.addItem(
                title           = title,
                autocomplete    = cmd,
                valid           = False
                )
        feedback.output()

    def tryShowMoreApps(self):
        sub = alfred.argv(1)
        for t in ['mac', 'ipad', 'iphone']:
            for item in more_apps_feed:
                title = item['title'].format(**more_apps_types[t])
                cmd = '-'.join(title.lower().split(' '))
                if sub == cmd:
                    feed = item['feed'].format(**more_apps_types[t])
                    # print feed
                    self.showAppsFromFeed(feed)
                    alfred.exit()

if __name__ == '__main__':
    App().run()