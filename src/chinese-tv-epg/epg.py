#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, os, re
import json
import warnings
import re
from datetime import datetime, timedelta

import alfred
alfred.setDefaultEncodingUTF8()

import bs4
from pprint import pprint

_baseurl = 'http://tv.cntv.cn/epg'

_default_favs = ['cctv1', 'cctv2', 'cctv3']

def parseWebPage(url, **kwargs):
    try:
        res = alfred.request.get(url, **kwargs)
        content = res.getContent()
        # HACK: 获取节目列表的网页HTML TAG 错误可能造成beautiful soup解析死循环
        # 需手动修改
        content = re.sub(r'<a>\n', '</a>\n', content)
        # 禁止显示BeautifulSoup警告
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return bs4.BeautifulSoup(content, fromEncoding='utf-8')
    except Exception, e:
        raise e

def fetchChannels():
    cache = alfred.cache.get('channels-list')
    if cache:
        return cache;
    soup = parseWebPage(_baseurl)
    channels = {}
    for item in soup.select('div.md_left_right'):
        dl_tag = item.find('dl')
        # 城市
        if dl_tag.attrs.get('id', '') == 'cityList':
            channel_tags = item.select('div.lv3 p a')
        else:
            channel_tags = item.select('dd a')
        for c_tag in channel_tags:
            chl_title = c_tag.get_text().strip()
            chl_id = c_tag.attrs['rel'][0]
            channels.update({chl_id:chl_title})
    if channels:
        # 缓存24小时
        alfred.cache.set('channels-list', channels, 3600*24)
    return channels

def fetchChannelEPG(channel, date, cache_name):
    cache = alfred.cache.get(cache_name)
    date_str = date.strftime('%Y-%m-%d')
    if cache and cache['date']==date_str:
        return cache['epg']
    data = {
            'action'    : 'epg-list',
            'date'      : date_str,
            'channel'   : channel
        }
    schedules = []
    soup = parseWebPage(
        'http://tv.cntv.cn/index.php', 
        data=data,
        referer=_baseurl
        )
    epg_list = soup.select('dl dd')
    schedules = []
    for item in epg_list:
        # 已播放的
        a_tags = item.select('a')
        sche_info = (a_tags[0] if a_tags else item).get_text().strip()
        first_space = sche_info.find(' ')
        if first_space < 0:
            continue
        schedules.append({
            'time' : sche_info[0:first_space].strip(),
            'show' : sche_info[first_space:].strip()
            })
    if not schedules:
        return
    alfred.cache.set(cache_name, {'date':date_str, 'epg':schedules}, 3600*24)
    return schedules


def fetchChannelEPGToday(channel):
    cache_name = '{}-today'.format(channel)
    date = datetime.now()
    return fetchChannelEPG(channel, date, cache_name)

def fetchChannelEPGTomorrow(channel):
    cache_name = '{}-tomorrow'.format(channel)
    date = datetime.now() + timedelta(days=1)
    return fetchChannelEPG(channel, date, cache_name)

def getChannelList():
    return fetchChannels()

def getChannelTitle(channel):
    channels = getChannelList()
    if channels.has_key(channel):
        return channels[channel]

# 获取正在和下一个将要播放的节目
def getCurrentAndNextProgram(channel):
    schedules = fetchChannelEPGToday(channel)
    if not schedules:
        return {}, {}
    current = {}
    next = {}
    schedules = sorted(schedules, key=lambda s:s['time'])
    now = datetime.now()
    for item in schedules:
        try:
            time = item['time'].split(':')
            hour = int(time[0])
            minute = int(time[1])
            if (hour==now.hour and minute>now.minute) or hour>now.hour:
                next = item
                break
            current = item
        except Exception, e:
            raise e
    return current, next

def getFavChannels():
    favs = alfred.config.get('fav')
    channels = getChannelList()
    if isinstance(favs, list):
        # 去除不在列表的频道
        favs = filter(lambda c: c in channels.keys(), favs)
        alfred.config.set(fav=favs)
        return favs
    # 还没有收藏频道
    favs = _default_favs
    alfred.config.set(fav=favs)
    return favs

def isChannelFaved(channel):
    return channel in getFavChannels()
    
def showLive():
    favs = getFavChannels()
    if not favs: alfred.exit()
    feedback = alfred.Feedback()
    for channel in favs:
        chl_title = getChannelTitle(channel)
        if not chl_title:
            continue
        cur, next = getCurrentAndNextProgram(channel)
        title = '{}'.format(chl_title)
        if cur:
            title = '{} 正在播放: {}'.format(chl_title, cur['show'])
        subtitle = ''
        if next:
            subtitle = '下一个节目: {time} {show}'.format(**next)
        feedback.addItem(
            title           = title,
            subtitle        = subtitle,
            autocomplete    = 'epg {}'.format(channel),
            valid           = False
            )
    feedback.addItem(
        title               = '显示所有电视频道',
        autocomplete        = 'all',
        valid               = False
        )
    feedback.addItem(
        title               = '显示收藏的电视频道',
        autocomplete        = 'fav',
        valid               = False
        )
    feedback.output()

def showAllChannles():
    channels = getChannelList()
    title_orded = sorted(channels.values(), key=lambda t: t.lower())
    def title_id(title):
        for k,v in channels.iteritems():
            if v==title:
                return k
    favs = getFavChannels()
    feedback = alfred.Feedback()
    for chl_title in title_orded:
        chl_id = title_id(chl_title)
        subtitle = '已收藏' if chl_id in favs else ''
        feedback.addItem(
            title           = chl_title,
            subtitle        = subtitle,
            autocomplete    = 'epg {}'.format(chl_id),
            valid           = False
            )
    feedback.output()

# 显示某频道或收藏的频道列表
def showEPG():
    channel = alfred.argv(2)
    if channel:
        return showChannleEPG(channel)
    favs = getFavChannels()
    if not favs: alfred.exitWithFeedback(title='你还没有收藏的频道')
    feedback = alfred.Feedback()
    for chl_id in favs:
        current, next = getCurrentAndNextProgram(chl_id)
        subtitle = '正在播放: {show}'.format(**current) if current else ''
        feedback.addItem(
            title           = getChannelTitle(chl_id),
            subtitle        = subtitle, 
            arg             = chl_id,
            autocomplete    = 'epg {}'.format(chl_id),
            valid           = False
            )
    feedback.output()
    

# 显示频道节目单
def showChannleEPG(channel):
    chl_title = getChannelTitle(channel)
    if not chl_title: alfred.exitWithFeedback(title='未找到频道信息')
    schedules = fetchChannelEPGToday(channel)
    if not schedules: alfred.exitWithFeedback(title='未找到频道的节目单')
    feedback = alfred.Feedback()
    date_str = datetime.now().strftime('%Y-%m-%d')
    now_time = datetime.now().strftime('%H:%M')
    is_faved = isChannelFaved(channel)
    feedback.addItem(
        title       = '{} {} 节目单 现在时间: {}'.format(chl_title, date_str, now_time),
        subtitle    = '已收藏，选择这项可以取消收藏。' if is_faved else '未收藏，选择这项可以收藏',
        arg         = 'toggle-fav {}'.format(channel)
        )
    for item in schedules:
        feedback.addItem(
            title = '{time} {show}'.format(**item)
            )
    feedback.output()

def main():
    cmd_map = {
        'live'              : lambda: showLive(),
        'epg'               : lambda: showEPG(),
        'fav'               : lambda: showEPG(),
        'all'               : lambda: showAllChannles(),
    }
    cmd = alfred.argv(1)
    if not cmd or cmd.lower() not in cmd_map.keys():
        cmd = 'live'
    cmd_map[cmd.lower()]()

if __name__ == '__main__':
    main()