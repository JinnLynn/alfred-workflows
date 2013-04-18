#!/usr/bin/env python
# -*- coding: utf-8 -*-
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

__version__ = '2.0'

default_pages = [
    {
        'title' : 'Apps Going Free for Mac',
        'page'  : 'mac/all/prices/free/',
        'cmd'   : 'apps-going-free-for-mac'
    },
    {
        'title' : 'Apps Going Free for iPhone',
        'page'  : 'iphone/all/prices/free/',
        'cmd'   : 'apps-going-free-for-iphone'
    },
    {
        'title' : 'Apps Going Free for iPad',
        'page'  : 'ipad/all/prices/free/',
        'cmd'   : 'apps-going-free-for-ipad'
    },
]

more_apps_pages = [
    {
        'title' : 'Popular Changes for {title}',
        'page'  : '',
    },
    {
        'title' : 'Popular New Apps for {title}',
        'page'  : 'new/',
    },
    {
        'title' : 'Popular New Apps (Free) for {title}',
        'page'  : 'new/free/',
    },
    {
        'title' : 'Popular New Apps (Paid) for {title}',
        'page'  : 'new/paid/',
    },
    {
        'title' : 'Popular Updates for {title}',
        'page'  : 'updates/',
    },
    {
        'title' : 'Popular Price Drops for {title}',
        'page'  : 'prices/',
    },
    {
        'title' : 'All Changes for {title}',
        'page'  : 'all/',
    },
    {
        'title' : 'All New Apps for {title}',
        'page'  : 'all/new/',
    },
    {
        'title' : 'All New Apps (Free) for {title}',
        'page'  : 'all/new/free/',
    },
    {
        'title' : 'All New Apps (Paid) for {title}',
        'page'  : 'all/new/paid/',
    },
    {
        'title' : 'All Updates for {title}',
        'page'  : 'all/updates/',
    },
    {
        'title' : 'All Price Drops for {title}',
        'page'  : 'all/prices',
    }
]

more_apps_page_type = {
    'mac'   : {'title':'Mac', 'platform':'mac', 'device':''},
    'ipad'  : {'title':'iPad', 'platform':'', 'device':'ipad'},
    'iphone': {'title':'iPhone', 'platform':'', 'device':'iphone'}
}

country_currency = {
    'US':'United States/USD','CA':'Canada/CAD','DE':'Deutschland/EUR','UK':'United Kingdom/GBP',
    'AU':'Australia/AUD','AT':'Austria/EUR','IT':'Italia/EUR','JP':'Japan/JPY','AR':'Argentina/USD',
    'AM':'Armenia/USD','BE':'Belgium/EUR','BW':'Botswana/USD','BR':'Brazil/USD','BG':'Bulgaria/EUR',
    'CL':'Chile/USD','CN':'China/CNY','CO':'Colombia/USD','CR':'Costa Rica/USD','HR':'Croatia/USD',
    'CZ':'Czech Republic/EUR','DK':'Denmark/DKK','DO':'Dominican Republic/USD','EC':'Ecuador/USD',
    'SV':'El Salvador/USD','EG':'Egypt/USD','EE':'Estonia/EUR','FI':'Finland/EUR','FR':'France/EUR',
    'GT':'Guatemala/USD','GR':'Greece/EUR','HN':'Honduras/USD','HK':'Hong Kong/HKD','HU':'Hungary/EUR',
    'IN':'India/INR','ID':'Indonesia/IDR','IE':'Ireland/EUR','IL':'Israel/ILS','JM':'Jamaica/USD',
    'JO':'Jordan/USD','KZ':'Kazakhstan/USD','KE':'Kenya/USD','KP':'Korea (north)/USD',
    'KR':'Korea (south)/USD','KW':'Kuwait/USD','LV':'Latvia/EUR','LB':'Lebanon/USD','LT':'Lithuania/EUR',
    'LU':'Luxembourg/EUR','MO':'Macau/USD','MK':'Macedonia/USD','MG':'Madagascar/USD','MY':'Malaysia/USD',
    'MT':'Malta (Republic of)/EUR','ML':'Mali/USD','MU':'Mauritius/USD','MX':'Mexico/MXP',
    'MD':'Moldova/USD','NL':'Netherlands/EUR','NZ':'New Zealand/NZD','NI':'Nicaragua/USD','NE':'Niger/USD',
    'NO':'Norway/NOK','PK':'Pakistan/USD','PA':'Panama/USD','PY':'Paraguay/USD','PE':'Peru/USD',
    'PH':'Philippines/USD','PL':'Poland/EUR','PT':'Portugal/EUR','QA':'Qatar/USD','RO':'Romania/EUR',
    'RU':'Russia/RUB','SA':'Saudi Arabia/SAR','SN':'Senegal/USD','SG':'Singapore/SGD','SK':'Slovakia/EUR',
    'SI':'Slovenia/EUR','ZA':'South Africa/ZAR','ES':'Spain/EUR','LK':'Sri Lanka/USD','SE':'Sweden/SEK',
    'CH':'Switzerland/CHF','TW':'Taiwan/TWD','TH':'Thailand/USD','TN':'Tunisia/USD','TR':'Turkey/TRY',
    'AE':'UAE/AED','UG':'Uganda/USD','UY':'Uruguay/USD','VE':'Venezuela/USD','VN':'Vietnam/USD'
    }

class App(object):
    def __init__(self):
        self.enable_appiconshow = alfred.config.get('app_icon_show', True)

    def run(self):
        cmd = alfred.argv(1)
        if not cmd:
            return self.showDefaultList()
        cmd = cmd.lower()
        for page in default_pages:
            if cmd == page['cmd']:
                url = os.path.join('http://appshopper.com', page['page'])
                self.showAppsFromPage(url)
                alfred.exit()

        self.tryShowMoreApps()

        if cmd.startswith('search'):
            cmd = 'search'
        if cmd.startswith('more-apps-'):
            cmd = 'more-apps'

        cmd_map = {
            'search'            : lambda: self.search(),
            'wishlist'          : lambda: self.showWishList(),
            'setting'           : lambda: self.showSettings(),
            'more-apps'         : lambda: self.showMoreApps(),
            'change-country'    : lambda: self.showCountries()
        }
        if cmd in cmd_map.keys():
            return cmd_map[cmd]()
        return self.showDefaultList()

    def getCountry(self):
        country = alfred.config.get('country', 'US')
        if country not in country_currency.keys():
            alfred.config.delete('country')
            return 'US'
        return country

    def getContryDesc(self):
        return country_currency[self.getCountry()]

    def openUrl(self, url):
        opener = urllib2.build_opener()
        cookie = 'AS_country={}; expires=Thu, 12 Dec 2030 00:00:00 ; path=/'.format(self.getCountry())
        opener.addheaders.append(('Cookie', cookie))
        content = opener.open(url).read()
        return content

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

                pricedrop_tag = item.select('.pricedrop')
                pricedrop = ''
                if pricedrop_tag:
                    pricedrop_tag = pricedrop_tag[0]
                    pricedrop_cents = pricedrop_tag.find('sup').get_text()
                    if pricedrop_cents:
                        pricedrop_cents = '.{}'.format(pricedrop_cents)
                    pricedrop_tag.find('sup').extract()
                    pricedrop = pricedrop_tag.get_text()
                    pricedrop = '{}{}'.format(pricedrop, pricedrop_cents)

                app_price_info = app_price
                if pricedrop:
                    app_price_info = '{} -> {}'.format(pricedrop, app_price_info)

                app_category = item.select('.category')[0].string.strip()
                app_lastchange = item.find_all('dd')[0].get_text()
                app_rating = item.find_all('dd')[1].get_text()
                app_version = item.find_all('dd')[2].get_text()
                app_device = item.select('dl > dt > nobr')[0].string.strip()

                icon_tag = item.find('img')
                app_icon = icon_tag['src'].strip()
                app_link = icon_tag.find_parent('a')['href'].strip()

                app_desc = 'Price: {}  Version: {}  Rating: {}  Category: {}  Device: {}'.format(
                    app_price_info, app_version, app_rating, app_category, app_device)
            except Exception, e:
                continue
            data.append({
                'name'      : app_name,
                'link'      : app_link,
                'desc'      : app_desc,
                'icon'      : app_icon,
                'store'     : app_store_link,
                'category'  : app_category
                })
        if cached and data:
            alfred.cache.set(page, data, CACHE_EXPIRE)
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
        alfred.storage.batchDownload(links)

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
                autocomplete    = 'wishlist',
                valid           = False
                )
        for item in default_pages:
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

    def showAppsFromPage(self, page):
        success, data = self.fetchDataFromePage(page)
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
        feedback.addItem(
            title           = 'Change Country/Currency',
            subtitle        = 'current: {}'.format( self.getContryDesc() ),
            autocomplete    = 'change-country',
            valid           = False
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
        if t not in more_apps_page_type.keys():
            self.exitWithFeedback(
                title = 'Nothing found'
                )
        feedback = alfred.Feedback()
        for item in more_apps_pages:
            title = item['title'].format(**more_apps_page_type[t])
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
            for item in more_apps_pages:
                title = item['title'].format(**more_apps_page_type[t])
                cmd = '-'.join(title.lower().split(' '))
                if sub != cmd:
                    continue
                page_url = os.path.join(
                    'http://appshopper.com', 
                    more_apps_page_type[t]['platform'],
                    more_apps_page_type[t]['device'],
                    item['page']
                    )
                self.showAppsFromPage(page_url)
                alfred.exit()

    def showCountries(self):
        q = alfred.argv(2)
        feedback = alfred.Feedback()
        for k,v in country_currency.iteritems():
            if q and not q.lower() in v.lower():
                continue
            feedback.addItem(
                title   = v,
                arg     = 'change-country {}'.format(k)
                )
        feedback.items.sort(key=lambda i: i.content['title'].lower())
        feedback.output()

if __name__ == '__main__':
    App().run()