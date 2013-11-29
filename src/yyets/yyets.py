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

__version__ = '1.5.1'

_base_host = 'http://www.yyets.com/'

_fb_return = lambda: getReturnLastQueryFeedbackItem()
_fb_return_top = lambda: alfred.Item(title='返回', valid=False, autocomplete=' ')
_fb_no_found = lambda: getReturnLastQueryFeedbackItem('没有找到想要的内容')
_fb_no_logined = lambda: alfred.Item(title='需要登录才能查看', subtitle='选择设置用户名和密码', valid=False, autocomplete='setting ')

# 资源模版
_res_tpl = {
    'id'    : 0,
    'title' : '',
    'img'   : '',
    'page'  : 0,
    'info'  : '',
    'files' : []
}
_res_file_tpl = {
    'id'        : 0,
    'info'      : '',
    'type'      : '',
    'format'    : '',
    'filename'  : '',
    'filesize'  : '',
    'emule'     : '',
    'magnet'    : '',
    'baidu'     : '',
    'update_date' : ''
}

def recordQuery():
    current = sys.argv[1:]
    queries = alfred.cache.get('record-query', {})
    last = queries.get('current', '')
    # 不同时才记录
    if current != last:
        queries.update(
            current = current,
            last    = last
        )
    alfred.cache.set('record-query', queries, 600)

def getReturnLastQueryFeedbackItem(title='返回', subtitle='回到上一个操作'):
    last_query = alfred.cache.get('record-query', {}).get('last', [])
    return alfred.Item(
        title       = title,
        subtitle    = subtitle,
        valid       = False,
        autocomplete = ' '.join(last_query)
    )

def login():
    alfred.cache.delete('cookie')
    usr = alfred.config.get('usr')
    pwd = alfred.config.get('pwd')
    if not usr or not pwd:
        return False
    try:
        res = alfred.request.post(
            _base_host + 'user/login/ajaxLogin',
            data = {
                'type'      : 'nickname',
                'account'   : usr,
                'password'  : pwd,
                'remember'  : 1
            }
        )
        ret = json.loads(res.getContent())
        if ret.get('status', 0) == 1:
            cookies = {}
            for c in res.cookieJar:
                if c.name in ['GINFO', 'GKEY']:
                    cookies[c.name] = c.value
            alfred.cache.set('cookie', cookies, 3600)
            return True
    except Exception, e:
        pass

def getLoginCookies():
    cache = alfred.cache.get('cookie')
    if cache:
        return cache
    login()
    return alfred.cache.get('cookie')

def isLogined():
    return bool(getLoginCookies())

def parseWebPage(url, **kwargs):
    try:
        if not kwargs.has_key('cookie') and isLogined():
            kwargs['cookie'] = getLoginCookies()
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

# 解析下载地址
# links 为下载链接bs4对象集合
def parseDownloadLink(links):
    dls = {}
    for link in links:
        href = link.get('href', '')
        if href.startswith('ed2k'):
            dls['emule'] = href
        elif href.startswith('magnet'):
            dls['magnet'] = href
        elif href.startswith('http://pan.baidu.com/'):
            dls['baidu'] = href
    return dls

def parseDownloadHas(data):
    has = {}
    for i in ['emule', 'magnet', 'baidu']:
        has['has_' + i] = '有' if data[i] else '无'
    return has

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
    alfred.cache.set(cache_name, items, 600)
    return items


# 获取今日更新（包括昨日与前天）
def fetchTodayItems():
    cache = alfred.cache.get('today-items')
    if cache:
        return cache
    items = []
    soup = parseWebPage('http://www.yyets.com/today')
    for single in soup.select('table tr.list'):
        info = single.select('td')
        item = {}
        item.update(**_res_file_tpl)
        item.update(
            type        = info[0].get_text(),
            format      = info[1].get_text(),
            filename    = info[2].find('a').get_text(),
            filesize    = info[4].get_text(),
            update_date = '{} {}'.format(single['day'], info[5].get_text())
        )
        res_id = os.path.basename(info[2].find('a')['href'])
        # 文件ID 页面没有提供 自定义 资源ID+hash
        item_id ='{}-{}'.format(res_id, alfred.util.hashDigest(res_id + item['filename']))
        item['id'] = item_id
        item.update(**parseDownloadLink( single.select('td.dr_ico a') ))
        items.append(item)
    if not items:
        return []
    # 缓存
    alfred.cache.set('today-items', items, 600) 
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
    # 缓存10分钟
    alfred.cache.set('top-items', items, 600)
    return items

# 获取单个资源信息
def fetchSingleResource(res_id):
    cache_name = 'single-resource-{}'.format(res_id)
    cache = alfred.cache.get(cache_name)
    if cache:
        return cache
    page_url = getResourcePageURLByID(res_id)
    soup = parseWebPage(page_url)
    # soup = soup.find('div', class_='AreaLL')
    res = {}
    res.update(**_res_tpl)
    res.update(
        id      = res_id,
        title   = soup.select('h2 strong')[0].get_text('', strip=True),
        img     = smallPosterURL(soup.select('div.res_infobox div.f_l_img img')[0]['src']),
        page    = page_url
    )
    for single in soup.select('ul.resod_list li'):
        item = {}
        item.update(**_res_file_tpl)
        item.update(
            id      = single['itemid'],
            format  = single['format'],
            filename = single.select('div.lks .lks-1')[0].get_text(),
            filesize = single.select('div.lks .lks-2')[0].get_text(),
        )
        for dl in single.select('div.download a'):
            dl_t = dl.get('type', '')
            href = dl.get('href', '')
            if dl_t == 'ed2k':
                item['emule'] = href
            if dl_t == 'magnet':
                item['magnet'] = href
            if href.startswith('http://pan.baidu.com'):
                item['baidu'] = href
        res['files'].append(item)
    # 缓存60分钟
    if res['files']: 
        alfred.cache.set(cache_name, res, 600)
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
    try:
        items = fetchRecentItems(alfred.argv(2))
        if not items:
            alfred.exitWithFeedback(item=_fb_no_found())
        feedback = alfred.Feedback()
        for item in items:
            feedback.addItem(
                title           = item['title'],
                subtitle        = item['info'],
                icon            = alfred.storage.getLocalIfExists(item['img'], True),
                valid           = False,
                autocomplete    = 'resource {} '.format(item['id'])
            )
        feedback.addItem(item=_fb_return_top())
        feedback.output()
    except Exception, e:
        alfred.exitWithFeedback(item=_fb_no_found()) 

# 最近今日更新
def today():
    if not isLogined():
        alfred.exitWithFeedback(item=_fb_no_logined())
    try:
        items = fetchTodayItems()
        filter_str = alfred.argv(2)
        if filter_str:
            filter_str = filter_str.upper()
            items = filter(lambda i: filter_str in i['format'], items)
        if not items:
            alfred.exitWithFeedback(item=_fb_no_found())
        feedback = alfred.Feedback()
        for item in items:
            item.update(**parseDownloadHas(item))
            subtitle = '类别: {type}  格式: {format}  容量: {filesize} 电驴: {has_emule}  磁力链: {has_magnet} 百度盘: {has_baidu} 日期: {update_date}'.format(**item)
            feedback.addItem(
                title           = item['filename'],
                subtitle        = subtitle,
                valid           = False,
                autocomplete    = 'today-file {}'.format(item['id'])
            )
        feedback.addItem(item=_fb_return_top())
        feedback.output()
    except Exception, e:
        alfred.exitWithFeedback(item=_fb_no_found())   

# 24小时最热资源
def top():
    try:
        items = fetchTopItems()
        if not items:
            alfred.exitWithFeedback(item=_fb_no_found())
        feedback = alfred.Feedback()
        count = 1
        for item in items:
            feedback.addItem(
                title           = '{:02d}. {}'.format(count, item['title']),
                subtitle        = item['info'],
                icon            = alfred.storage.getLocalIfExists(item['img'], True),
                valid           = False,
                autocomplete    = 'resource {id} '.format(**item)
            )
            count = count + 1
        feedback.addItem(item=_fb_return_top())
        feedback.output()
    except Exception, e:
        alfred.exitWithFeedback(item=_fb_no_found())

def search():
    try:
        word = ' ' .join(sys.argv[2:])
        if not word:
            alfred.exitWithFeedback(title='输入搜索关键词')
        items = fetchSearchResult(word)
        if not items:
            alfred.exitWithFeedback(item=_fb_no_found())
        feedback = alfred.Feedback()
        for item in items:
            feedback.addItem(
                title           = item['title'],
                subtitle        = item['info'],
                valid           = False,
                autocomplete    = 'resource {} '.format(item['id'])
            )
        feedback.addItem(item=_fb_return_top())
        feedback.output()
    except Exception, e:
        alfred.exitWithFeedback(_fb_no_found())    

def resource():
    try:
        res_id = int(alfred.argv(2))
        data = fetchSingleResource(res_id)
        filter_str = alfred.argv(3)
        files = data.get('files', [])
        if filter_str:
            filter_str = filter_str.upper()
            files = filter(lambda f: filter_str in f['format'], files)
        if not data:
            alfred.exitWithFeedback(item=_fb_no_found)
        feedback = alfred.Feedback()
        feedback.addItem(
            title       = data['title'],
            subtitle    = '{} 个文件，可使用文件类型过滤，选择此项打开资源页面'.format(len(files)),
            arg         = 'open-url {}'.format( b64encode(getResourcePageURLByID(data['id'])) ),
            icon        = alfred.storage.getLocalIfExists(data['img'], True)
        )
        files_ids = []
        for f in files:
            files_ids.append(f['id'])
            f.update(**parseDownloadHas(f))
            subtitle = '类型: {format} 容量: {filesize} 电驴: {has_emule} 磁力链: {has_magnet} 百度盘: {has_baidu}'.format(**f)
            feedback.addItem(
                title           = f['filename'],
                subtitle        = subtitle,
                valid           = False,
                autocomplete    = 'file {},{}'.format(data['id'], f['id'])
            )
        if len(files_ids) > 1:
            feedback.addItem(
                title           = '所有文件',
                subtitle        = '对当前的所有文件进行批量处理',
                valid           = False,
                autocomplete    = 'file {},{}'.format(data['id'], ','.join(files_ids))
            )
        feedback.addItem(item=_fb_return())
        feedback.output()
    except Exception, e:
        alfred.exitWithFeedback(item=_fb_no_found())

def fileDownloadFeedback(feedback, res_id, emule, magnet, baidu=None):
    if baidu:
        feedback.addItem(
            title       = '打开百度盘',
            subtitle    = baidu,
            arg         = 'open-url {}'.format(b64encode(baidu))
        )
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
            arg         = 'open-url {}'.format( b64encode(getResourcePageURLByID(res_id)) )
        )
    return feedback

def file():
    try:
        ids = alfred.argv(2).split(',')
        res_id = int(ids[0])
        file_ids = map(lambda i:int(i), ids[1:])
        data = fetchSingleResource(res_id)
        files = filter(lambda f: int(f['id']) in file_ids, data['files'])

        feedback = alfred.Feedback()
        if not files:
            feedback.addItem(
                title           = '没有找到想要的内容',
                subtitle        = '这里可返回资源列表',
                valid           = False,
                autocomplete    = 'resource {} '.format(res_id),
                icon            = alfred.storage.getLocalIfExists(data['img'], True)
            )
        elif len(files) == 1:
            subtitle = '类型: {format} 容量: {filesize} 这里可返回资源列表'.format(**files[0])
            feedback.addItem(
                title           = files[0]['filename'],
                subtitle        = subtitle,
                valid           = False,
                autocomplete    = 'resource {} '.format(res_id),
                icon            = alfred.storage.getLocalIfExists(data['img'], True)
            )
            feedback = fileDownloadFeedback(feedback, data['page'], files[0]['emule'], files[0]['magnet'], files[0]['baidu'])
        else:
            feedback.addItem(
                title           = '批处理多个文件',
                subtitle        = '{} 个文件, 这里可返回资源列表'.format(len(files)),
                valid           = False,
                autocomplete    = 'resource {}'.format(res_id),
                icon            = alfred.storage.getLocalIfExists(data['img'], True)
            )
            emule = '\n'.join( [f['emule'] for f in files] )
            magnet = '\n'.join( [f['magnet'] for f in files] )
            feedback = fileDownloadFeedback(feedback, data['page'], emule, magnet)
        feedback.output()
    except Exception, e:
        alfred.exitWithFeedback(item=_fb_no_found())

def todayFile():
    if not isLogined():
        alfred.exitWithFeedback(item=_fb_no_logined())
    try:
        item_id = alfred.argv(2)
        res_id = item_id.split('-')[0]
        item = {}
        for item in fetchTodayItems():
            if item.get('id') == item_id:
                break
        if not item:
            alfred.exitWithFeedback(item=_fb_no_found())
        feedback = alfred.Feedback()
        feedback.addItem(
            title       = item['filename'],
            subtitle    = '类别: {type}  格式: {format}  容量: {filesize}  日期: {update_date} 这里可访问资源文件列表'.format(**item),
            valid           = False,
            autocomplete    = 'resource {}'.format(res_id)
        )
        feedback = fileDownloadFeedback(feedback, res_id, item['emule'], item['magnet'], item['baidu'])
        feedback.addItem(item=_fb_return())
        feedback.output()
    except Exception, e:
        alfred.exitWithFeedback(item=_fb_no_found())

def setting():
    usr = alfred.argv(2)
    pwd = alfred.argv(3)
    info = ''
    if usr:
        info = '用户名: {} 密码: {}'.format(usr, pwd)
    elif alfred.config.get('usr'):
        info = '现有设置: 用户名: {} 密码: ********'.format(alfred.config.get('usr'))
    feedback = alfred.Feedback()
    feedback.addItem(
        title       = '{}用户名和密码'.format('修改' if isLogined() else '设置'),
        subtitle    = '格式：用户名 密码 {}'.format(info),
        arg         = 'account-setting {} {}'.format(usr, pwd)
    )
    feedback.output()


def menu():
    feedback = alfred.Feedback()
    feedback.addItem(
        title           = '人人影视 24小时热门资源',
        subtitle        = '最近24小时的热门排行',
        autocomplete    = 'top',
        valid           = False
    )
    if isLogined():
        feedback.addItem(
            title           = '人人影视 今日更新的文件',
            subtitle        = '也包括昨日与前日更新的文件，可使用格式名称过滤文件，如hdtv, mp4, 1080p等',
            autocomplete    = 'today ',
            valid           = False
        )
    feedback.addItem(
        title           = '人人影视 最近更新的资源',
        subtitle        = '可使用movie, tv, documentary, openclass, topic过滤相应的资源',
        autocomplete    = 'recent ',
        valid           = False
    )
    feedback.addItem(
        title           = '人人影视 资源搜索...',
        subtitle        = '',
        autocomplete    = 'search ',
        valid           = False
    )

    feedback.addItem(
        title           = '{}用户名和密码'.format('修改' if isLogined() else '设置'),
        subtitle        = '{}查看今日更新文件或某些有版权问题需要，仅支持用户名方式登陆'.format('已设置并成功登陆，' if isLogined() else ' '),
        valid           = False,
        autocomplete    = 'setting '
    )
    feedback.output()

def main():
    alfred.cache.cleanExpired()
    cmds = {
        'menu'      : menu,
        'recent'    : recent,
        'top'       : top,
        'search'    : search,
        'resource'  : resource,
        'file'      : file,
        'today'     : today,
        'today-file': todayFile,
        'setting'   : setting
    }
    subcmd = alfred.argv(1) or ''
    subcmd = subcmd.lower()
    # 空 或 有意义的命令才记录
    if not subcmd or subcmd in cmds:
        recordQuery()
    cmds[subcmd]() if subcmd in cmds else cmds['menu']()

if __name__ == '__main__':
    main()