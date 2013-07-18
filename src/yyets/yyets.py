#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import warnings
import time
import json
from base64 import b64encode, b64decode
import os
from pprint import pprint

import alfred
alfred.setDefaultEncodingUTF8()
import bs4

_fb_return_top = alfred.Item(title='返回', subtitle='', valid=False, autocomplete='')
_fb_no_found = alfred.Item(title='没有找到想要的内容', subtitle='', valid=False)
_fb_no_found_and_return_top = alfred.Item(title='没有找到想要的内容', subtitle='选择返回', valid=False, autocomplete='')

def parseWebPage(url, **kwargs):
    try:
        res = alfred.request.get(url, **kwargs)
        content = res.getContent()
        # 禁止显示BeautifulSoup警告
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return bs4.BeautifulSoup(content)
    except Exception, e:
        raise e

# 小海报地址获取
# 文件名的第一位字母标识海报大小 s m b
def smallPosterURL(url):
    if not url:
        return url
    dirname = os.path.dirname(url)
    basename = os.path.basename(url)
    if basename.startswith('s'):
        return url
    s_basename = '{}{}'.format('s', basename[1:])
    return os.path.join(dirname, s_basename)

# 获取最新更新
def fetchRecentItems(channel):
    # channel: movie tv documentary openclass topic
    search_channel = ''
    # 如果查找的类别不为空的话，获取其完整的正确名称
    if channel:
        for valid_chl in ['movie', 'tv', 'documentary', 'openclass', 'topic']:
            if valid_chl.startswith(channel):
                search_channel = valid_chl
        if not search_channel:
            return []
    cache_name = 'recent-{}-items'.format(search_channel)
    cache = alfred.cache.get(cache_name)
    if cache:
        return cache
    items = []
    soup = parseWebPage(
        'http://www.yyets.com/resourcelist',
        data = {
            'channel'   : search_channel,
            'sort'      : 'update'
        }
    )
    # pprint(soup.select('ul.boxPadd li'))
    for single in soup.select('ul.boxPadd li'):
        item = {}
        try:
            # 图片 页面地址
            item['page'] = single.select('div.f_l_img')[0].a['href']
            item['img'] = smallPosterURL( single.select('div.f_l_img')[0].img['src'] )
            top_str = single.select('div.f_l_img')[0].get_text()
            item['id'] = os.path.basename(item['page'])
            info = single.select('div.f_r_info dl')[0]
            # 标题
            item['title'] = info.dt.get_text(' ', strip=True)
            map(lambda t: t.font.clear(),info.dd.select('span'))
            # 说明 人气
            item['info'] = '说明: {} 人气: {}'.format(   
                info.dd.select('span')[0].get_text('', strip=True),
                info.dd.select('span')[2].get_text('', strip=True)
            )
            items.append(item)
        except Exception, e:
            # 忽略错误
            continue
    if not items:
        return []
    # 缓存10分钟
    alfred.cache.set(cache_name, items, 60*10)
    return items


# 获取今日更新（包括昨日与前天）
def fetchTodayItems():
    cache = alfred.cache.get('today-items')
    if cache:
        return cache
    items = []
    soup = parseWebPage('http://www.yyets.com/html/today.html')
    for single in soup.select('div.day_data tr.list'):
        item = {}
        info = single.select('td')
        # 类别
        item['type'] = info[0].get_text()
        # 格式
        item['format'] = info[1].get_text()
        # 文件名 及 页面链接
        _tmp = info[2].find('a')
        if not _tmp:
            continue
        item['filename'] = _tmp.get_text()
        item['page'] = _tmp['href']
        # 下载链接 只关心电驴 和 磁力链
        item['emule'] = ''
        item['magnet'] = ''
        if info[3].select('a.c'):
            item['magnet'] = info[3].select('a.c')[0]['href']
        if info[3].select('a.l'):
            item['emule'] = info[3].select('a.l')[0]['href']
        # 容量
        item['size'] = info[4].get_text()
        # 更新时间
        item['date'] = '{} {}'.format(single['day'], info[5].get_text())
        items.append(item)
    if not items:
        return []
    # 缓存5分钟
    alfred.cache.set('today-items', items, 60*5) 
    return items

# 获取24小时热门榜
def fetchTopItems():
    cache = alfred.cache.get('top-items')
    if cache:
        return cache
    items = []
    soup = parseWebPage('http://www.yyets.com/resourcelist')
    for single in soup.select('ul.top_list2 li'):
        item = {}
        # 照片 页面链接
        img_ele = single.select('div.f_l_img')
        if img_ele:
            item['page'] = img_ele[0].a['href']
            item['img'] = smallPosterURL( img_ele[0].a.img['src'] )
        item['id'] = os.path.basename(item['page'])
        info = single.select('div.f_r_info div')
        if info:
            # 标题
            item['title'] = info[0].get_text().strip('《》')
            item['info'] = '{} {} {}'.format(info[1].get_text(), info[2].get_text(), info[3].get_text())
        # pprint(item)
        items.append(item)
    if not items:
        return []
    # 缓存5分钟
    alfred.cache.set('top-items', items, 60*5)
    return items

# 获取单个资源信息
def fetchSingleResource(res_id):
    # 缓存最近的一个
    cache = alfred.cache.get('single-resource')
    if cache and cache['id'] == res_id:
        return cache
    res = {
        'id'    : res_id,
        'title' : '',
        'img'   : '',
        'page'  : getResourcePageURLByID(res_id),
        'files' : []
    }
    soup = parseWebPage(res['page'])
    res['title'] = soup.select('h2 strong')[0].get_text('', strip=True)
    res['img'] = smallPosterURL(soup.select('div.res_infobox div.f_l_img img')[0]['src'])
    for single in soup.select('ul.resod_list li'):
        item = {}
        item['id'] = single['itemid']
        # 格式
        item['format'] = single['format']
        # 文件名
        item['filename'] = single.select('span.l span.a')[0].get_text()
        item['filesize'] = single.select('span.l span.b')[0].get_text()
        item['emule'] = ''
        item['magnet'] = ''
        for l in single.select('span.r a'):
            if not l.attrs.has_key('type'):
                continue
            if l['type'] == 'ed2k':
                item['emule'] = l['href']
            if l['type'] == 'magnet':
                item['magnet'] = l['href']
        res['files'].append(item)
    # 缓存30分钟
    if res['files']: 
        alfred.cache.set('single-resource', res, 60*30)
    return res

# 获取搜索结果
def fetchSearchResult(word):
    if not word:
        return []
    items = []
    soup = parseWebPage(
        'http://www.yyets.com/search/index',
        data = {
            'keyword'   : '{}'.format(word),
            'type'      : 'resource',
            'order'     : 'uptime'
        }
    )
    for single in soup.select('ul.allsearch li'):
        item = {}
        try:
            # 标题 页面地址
            item['title'] = single.select('div.all_search_li2')[0].get_text()
            item['page'] = single.select('div.all_search_li2')[0].a['href']
            item['id'] = os.path.basename(item['page'])
            # print(single.select('div.all_search_li3')[0].get_text())
            # 信息
            pub_time = time.localtime(float(single.select('span.time')[0].get_text().strip()))
            update_time = time.localtime(float(single.select('span.time')[1].get_text().strip()))
            item['info'] = '类型:{} 发布时间:{} 更新时间:{} {}'.format(
                single.select('div.all_search_li1')[0].get_text().strip(),
                time.strftime('%Y-%m-%d %H:%I', pub_time),
                time.strftime('%Y-%m-%d %H:%I', update_time),
                single.select('div.all_search_li3')[0].get_text().strip()
            )
        except Exception, e:
            # raise e
            # 忽略错误
            continue
        items.append(item)
    return items

def getResourcePageURLByID(res_id):
    return 'http://www.yyets.com/resource/{}'.format(res_id)

# 获取最新更新
def recent():
    feedback = alfred.Feedback()
    try:
        for item in fetchRecentItems(alfred.argv(2)):
            feedback.addItem(
                title           = item['title'],
                subtitle        = item['info'],
                icon            = alfred.storage.getLocalIfExists(item['img'], True),
                valid           = False,
                autocomplete    = 'resource {}'.format(item['id'])
            )
    except Exception, e:
        alfred.raiseWithFeedback()
    if feedback.isEmpty():
        feedback.addItem(title='对不起，没有找到内容。')
    feedback.output()

# 最近今日更新
def today():
    feedback = alfred.Feedback()
    try:
        filter_str = alfred.argv(2)
        if filter_str:
            filter_str = filter_str.upper()
        feedback = alfred.Feedback()
        for item in fetchTodayItems():
            if filter_str and filter_str not in item['format']:
                continue
            item['has_emule'] = '有' if item['emule'] else '无'
            item['has_magnet'] = '有' if item['magnet'] else '无'
            subtitle = '类别: {type}  格式: {format}  容量: {size}  日期: {date}  电驴: {has_emule}  磁力链: {has_magnet}'.format(**item)
            feedback.addItem(
                title           = item['filename'],
                subtitle        = subtitle,
                valid           = False,
                autocomplete    = 'today-file {}'.format(b64encode( json.dumps(item) ))
            )
    except Exception, e:
        alfred.raiseWithFeedback()
    if feedback.isEmpty():
        feedback.addItem(title='对不起，没有找到内容。')
    feedback.output()

# 24小时最热资源
def top():
    feedback = alfred.Feedback()
    try:
        for item in fetchTopItems():
            feedback.addItem(
                title           = item['title'],
                subtitle        = item['info'],
                icon            = alfred.storage.getLocalIfExists(item['img'], True),
                valid           = False,
                autocomplete    = 'resource {id}'.format(**item)
            )

    except Exception, e:
        alfred.raiseWithFeedback()
    if feedback.isEmpty():
        feedback.addItem(title='对不起，没有找到内容。')
    feedback.output()

def search():
    word = ' ' .join(sys.argv[2:])
    if not word:
        alfred.exitWithFeedback(title='输入搜索关键词')
    feedback = alfred.Feedback()
    try:
        for item in fetchSearchResult(word):
            feedback.addItem(
                title           = item['title'],
                subtitle        = item['info'],
                valid           = False,
                autocomplete    = 'resource {}'.format(item['id'])
            )
    except Exception, e:
        alfred.raiseWithFeedback()
    if feedback.isEmpty():
        feedback.addItem(title='对不起，没有找到内容。')
    feedback.output()

def resource():
    try:
        res_id = int(alfred.argv(2))
        data = fetchSingleResource(res_id)
        filter_str = alfred.argv(3)
        if filter_str:
            filter_str = filter_str.upper()
        if not data:
            alfred.exitWithFeedback(title='没有找到相关的内容')
        feedback = alfred.Feedback()
        feedback.addItem(
            title       = data['title'],
            subtitle    = '打开资源页面，可使用文件类型过滤',
            arg         = 'open-url {}'.format( b64encode(getResourcePageURLByID(data['id'])) ),
            icon        = alfred.storage.getLocalIfExists(data['img'], True)
        )
        for f in data['files']:
            if filter_str and filter_str not in f['format']:
                continue
            f['has_emule'] = '有' if f['emule'] else '无'
            f['has_magnet'] = '有' if f['magnet'] else '无'
            subtitle = '类型: {format} 容量: {filesize} 电驴: {has_emule} 磁力链: {has_magnet}'.format(**f)
            feedback.addItem(
                title           = f['filename'],
                subtitle        = subtitle,
                valid           = False,
                autocomplete    = 'file {},{}'.format(data['id'], f['id'])
            )
        feedback.addItem(item=_fb_return_top)
        feedback.output()
    except Exception, e:
        alfred.exitWithFeedback(item=_fb_no_found_and_return_top)

def fileDownloadFeedback(feedback, page, emule, magnet):
    if emule:
        feedback.addItem(
            title       = '拷贝eMule地址到剪切板',
            subtitle    = emule,
            arg         = 'copy-to-clipboard {}'.format(b64encode(emule))
        )
    if magnet:
        feedback.addItem(
            title       = '拷贝磁力链到剪切板',
            subtitle    = magnet,
            arg         = 'copy-to-clipboard {}'.format(b64encode(magnet))
        )
    # 使用download station Workflow 下载 eMule优先
    #? 如何判断workflow已安装
    if emule or magnet:
        feedback.addItem(
            title       = '使用Download Station Workflow下载',
            subtitle    = '优先使用电驴地址下载',
            arg         = 'download-with-ds {}'.format( b64encode(emule if emule else magnet))
        )
    if not emule and not magnet:
        feedback.addItem(
            title       = '没有找到电驴或磁力链地址，打开资源页面',
            arg         = 'open-url {}'.format( b64encode(page) )
        )
    return feedback

def file():
    try:
        fileinfo = {}
        ids = alfred.argv(2).split(',')
        res_id = int(ids[0])
        file_id = int(ids[1])
        data = fetchSingleResource(res_id)
        for f in data['files']:
            if int(f['id']) == file_id:
                fileinfo = f
                break
        feedback = alfred.Feedback()
        subtitle = '类型: {format} 容量: {filesize} 这里可返回资源列表'.format(**f)
        feedback.addItem(
            title           = fileinfo['filename'],
            subtitle        = subtitle,
            valid           = False,
            autocomplete    = 'resource {}'.format(res_id),
            icon            = alfred.storage.getLocalIfExists(data['img'], True)
        )
        feedback = fileDownloadFeedback(feedback, data['page'], fileinfo['emule'], fileinfo['magnet'])
        feedback.output()
    except Exception, e:
        raise e
        alfred.exitWithFeedback(title='没有找到相关的内容')

def todayFile():
    try:
        data = json.loads(b64decode(alfred.argv(2)))
        feedback = alfred.Feedback()
        feedback.addItem(
            title       = data['filename'],
            subtitle    = '类别: {type}  格式: {format}  容量: {size}  日期: {date} 这里可访问资源页面'.format(**data),
            arg         = 'open-url {}'.format(b64encode(data['page']))
        )
        feedback = fileDownloadFeedback(feedback, data['page'], data['emule'], data['magnet'])
        feedback.addItem(
            title           = '返回今日文件更新',
            subtitle        = '',
            valid           = False,
            autocomplete    = 'today'
        )
        feedback.output()
    except Exception, e:

        alfred.exitWithFeedback(title='没有找到相关内容')

def menu():
    feedback = alfred.Feedback()
    feedback.addItem(
        title           = '人人影视 24小时热门资源',
        subtitle        = '最近24小时的热门排行',
        autocomplete    = 'top',
        valid           = False
    )
    feedback.addItem(
        title           = '人人影视 今日更新的文件',
        subtitle        = '也包括昨日与前日更新的文件，可使用格式名称过滤文件，如hdtv, mp4, 1080p等',
        autocomplete    = 'today',
        valid           = False
    )
    feedback.addItem(
        title           = '人人影视 最近更新的资源',
        subtitle        = '可使用movie, tv, documentary, openclass, topic过滤相应的资源',
        autocomplete    = 'recent',
        valid           = False
    )
    feedback.addItem(
        title           = '人人影视 资源搜索...',
        subtitle        = '',
        autocomplete    = 'search ',
        valid           = False
    )
    feedback.output()

def main():
    cmds = {
        'menu'      : lambda: menu(),
        'recent'    : lambda: recent(),
        'today'     : lambda: today(),
        'top'       : lambda: top(),
        'search'    : lambda: search(),
        'resource'  : lambda: resource(),
        'file'      : lambda: file(),
        'today-file': lambda: todayFile()
    }
    subcmd = alfred.argv(1)
    if subcmd and subcmd.lower() in cmds.keys():
        cmds[subcmd.lower()]()
    else:
        cmds['menu']()

if __name__ == '__main__':
    main()