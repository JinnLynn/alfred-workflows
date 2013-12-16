#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, os, json
import time
from datetime import datetime
from base64 import b64encode
from pprint import pprint

import alfred
alfred.setDefaultEncodingUTF8()

__version__ = '1.4.0'

_base_host = 'http://www.kuaidi100.com/'

_expire_day = 3600 * 24
_expire_year = _expire_day * 365

_post_cache_name = lambda c, p: '-'.join([c, p])

_fb_return = lambda ac='': alfred.Item(title='返回', valid=False, autocomplete=ac)

def formatTimestamp(timestamp, format='%Y-%m-%d %H:%M:%S'):
    return datetime.fromtimestamp(timestamp).strftime(format)

def fetchURL(url, **kwargs):
    try:
        if not kwargs.has_key('referer'):
            kwargs.update(referer=_base_host)
        res = alfred.request.get(url, **kwargs)
        content = res.getContent()
        return content
    except Exception, e:
        pass

# 缓存是否过期
# 这里的过期跟alfred.cache不一样，last_success的差异可能有不同的过期时间
def isCacheOutdate(cache, success_expire, fail_expire):
    last_update = cache.get('last_update', 0)
    span = time.time() - last_update
    success = cache.get('last_success', False)
    expire = success_expire if success else fail_expire
    return span < 0 or span > expire

# 获取快递公司列表或信息
def getCompany(code=None, key=None):
    cache = alfred.cache.get('company')
    if not cache or isCacheOutdate(cache, _expire_day*7, 3600):
        alfred.config.delete('company')  # 删除保存在config中的数据 旧版的保存位置
        data = {}
        try:
            res = fetchURL(
                os.path.join(_base_host, 'js/share/company.js'),
                data = {
                    'version' : time.time()
                }
            )
            res = res.lstrip('var jsoncom=').rstrip(';').replace("'", '"')
            company = json.loads(res).get('company', [])
            if not company:
                raise Exception('something error.')
            data.update(
                last_success = True,
                company = company
            )
        except Exception, e:
            # 缓存存在 使用缓存 不在则从company.json获取
            if cache:
                company=cache.get('company')
            else:
                with open(os.path.abspath('./company.json'), 'r') as fp:
                    company=json.load(fp)
            data.update(last_success=False, company=company)
        data.update(last_update=time.time())
        alfred.cache.set('company', data, _expire_year)
    data = alfred.cache.get('company')
    if not code:
        return data.get('company')
    for company in data.get('company'):
        if company['code'] == code:
            return company if key is None else company.get(key, '')
    return ''

def getComponyLogo(code):
    path = os.path.abspath('./logos/{}.png'.format(code))
    if os.path.exists(path):
        return path

def getStoredPost(com_code, post_id):
    for p in alfred.config.get('post', []):
        if p.get('com_code') == com_code and p.get('post_id') == post_id:
            return p

# 运单是否是被存储的
def isPostStored(com_code, post_id):
    return bool(getStoredPost(com_code, post_id))

# 存储运单
def savePost(com_code, post_id):
    if isPostStored(com_code, post_id):
        return
    post = alfred.config.get('post', [])
    post.append({
        'com_code'  : com_code,
        'post_id'   : post_id,
        'remark'    : ''
    })
    alfred.config.set(post=post)

# 删除运单
def delPost(com_code, post_id):
    post = alfred.config.get('post', [])
    post = filter(lambda p: p.get('com_code') != com_code or p.get('post_id') != post_id, post)
    alfred.config.set(post=post)
    # 删除缓存
    alfred.cache.delete(_post_cache_name(com_code, post_id))
    # 清理过期的缓存 
    alfred.cache.cleanExpired()

# 清理已签收的运单
def clearCheckedPost():
    post = alfred.config.get('post', [])
    for p in post:
        q = querySingle(p['com_code'], p['post_id'])
        if q.get('checked', False):
            delPost(p['com_code'], p['post_id'])

# 修改运单备注
def changePostRemark(com_code, post_id, remark):
    if not isPostStored(com_code, post_id):
        return False
    post = alfred.config.get('post', [])
    for p in post:
        if p.get('com_code') == com_code and p.get('post_id') == post_id:
            p['remark'] = remark if isinstance(remark, basestring) and remark else ''
            break;
    alfred.config.set(post=post)
    return True

# 猜测公司代码
# 优先顺序: 代码 > 短名 > 全名
def surmiseCompanyCode(q):
    companies = getCompany()
    for k in ['code', 'shortname', 'companyname']:
        for com in companies:
            if com[k].lower() == q.lower():
                return com['code']
    return q

# 根据订单号猜测快递公司
def queryCompanyCodeByPostID(post_id):
    try:
        res = fetchURL(
            os.path.join(_base_host, 'autonumber/auto'),
            data = {
                'num' : post_id
            }
        )
        coms = json.loads(res)
        return [com['comCode'] for com in coms]
    except Exception, e:
        pass

# 查询某个特定运单
# success 是否曾成功获取过数据 last_success 最近一次是否成功获取数据
def querySingle(com_code, post_id):
    cache_name = _post_cache_name(com_code, post_id)
    cache = alfred.cache.get(cache_name)
    # 存在 且是 已经签收或未过期
    if cache and ( cache.get('checked', False) or not isCacheOutdate(cache, 60*30, 60) ):
        return cache
    data = {}
    try:
        res = fetchURL(
            os.path.join(_base_host, 'query'),
            data = {
                'type' : com_code,
                'postid' : post_id
            }
        )
        res = json.loads(res)
        # 失败抛出一个异常
        if res['status'] != '200':
            raise Exception(res['message'])

        com = getCompany(res['com'])
        data.update(
            success = True,
            last_success = True,
            last_message = '',
            post_id = res['nu'],
            checked = True if res['ischeck'] == '1' else False,
            com_code = res['com'],
            com_name = com.get('companyname', '未知'),
            com_shortname = com.get('shortname', '未知'),
            trace = [{'time':t['ftime'], 'content':t['context']} for t in res.get('data', [])]
        )
    except Exception, e:
        # 失败 检查缓存 若有 更新 否则创建
        data.update(cache if cache else {'success':False})
        data.update(last_message=str(e), last_success=False)
    data.update(last_update=time.time())
    # 缓存长期保存 防止已有成功查询后出现失败的查询无法使用先前的成功结果
    # 是否过期通过last_update
    # 如果success=False即尚未有成功的查询 则缩短缓存有效期 
    # 防止某些非需要的运单号(如输入单号过程中或错误的单号)被长期记录在缓存中
    expire = _expire_day*7 if data.get('success', False) else 60
    alfred.cache.set(cache_name, data, expire)
    return data

# 显示快递公司列表
def showCompanyList():
    key = alfred.argv(2)
    companies = getCompany()
    if key:
        key = key.lower()
        companies = filter(lambda c: key in c['companyname'].lower() or key in c['code'], companies)
    if not companies:
        alfred.exitWithFeedback(title='没有找到相关的内容')
    feedback = alfred.Feedback()
    for com in companies:
        feedback.addItem(
            title       = com['companyname'],
            subtitle    = '代码: {} 电话: {} 官方网站: {}'.format(com['code'], com['tel'], com['comurl']),
            icon        = getComponyLogo(com['code']),
            arg         = 'open-url {}'.format(b64encode(com['comurl']))
        )
    feedback.output()

# 显示存储的快递单
def showSaved():
    post = alfred.config.get('post')
    feedback = alfred.Feedback()
    has_checked = False
    if post:
        for p in post[::-1]:
            q = querySingle(p['com_code'], p['post_id'])
            if q.get('checked', False):
                has_checked = True
            item = {}
            item.update(
                title           = '{} {} {}'.format(getCompany(p['com_code'], 'companyname'), p['post_id'], p.get('remark', '')),
                icon            = getComponyLogo(p['com_code']),
                valid           = False,
                autocomplete    = '{} {}'.format(p['com_code'], p['post_id'])
            )
            if q.get('success'):
                item['subtitle'] = '{time} {content}'.format(**q['trace'][0])
            else:
                item['subtitle'] = '{} 暂时没有记录，运单号不存在、未记录或已经过期。'.format(formatTimestamp(q['last_update']))
            feedback.addItem(**item)
        # 有已签收的
        if has_checked:
            feedback.addItem(
                title   = '清除所有已签收的运单？',
                arg     = 'clear-checked-post'
            )
    else:
        feedback.addItem(
            title       = '国内快递查询',
            subtitle    = '直接使用运单号，如:904080779005，快递公司+运单号，如:顺风 904080779005',
            valid       = False
        )
    feedback.output()

def showSingle(com_code, post_id):
    data = querySingle(com_code, post_id)
    post_info = '{} {}'.format(getCompany(com_code, 'companyname'), post_id)
    feedback = alfred.Feedback()
    if not data.get('success'):
        feedback.addItem(
            title       = '查询失败: {}'.format(post_info),
            subtitle    = '{} {}'.format(formatTimestamp(data['last_update']), data.get('last_message', '')),
            icon        = os.path.abspath('./icon-error.png'),
            valid       = False
        )
    else:
        # 查询成功 自动保存运单方便下次查询
        savePost(com_code, post_id)
        post = getStoredPost(com_code, post_id)
        remark = post.get('remark', '')
        last_update_info = '' if data.get('last_success') else '本次查询失败，下面显示的是先前的查询结果。'
        update_info = '已签收 ' if data['checked'] else last_update_info
        feedback.addItem(
            title       = '{} {}'.format(post_info, remark),
            subtitle    = '最后查询: {} {}'.format(
                formatTimestamp(data['last_update']), 
                update_info
            ),
            icon        = getComponyLogo(com_code),
            valid       = False
        )
        count = len(data['trace'])
        for t in data['trace']:
            feedback.addItem(
                title       = '{:02d}. {}'.format(count, t['content']), 
                subtitle    = t['time'],
                valid       = False
            )
            count = count - 1
    # 运单是否保存
    stored = isPostStored(com_code, post_id)
    # 已保存的 可添加或修改备注
    if stored:
        post = getStoredPost(com_code, post_id)
        remark = post.get('remark')
        remark = '当前备注: {}'.format(remark) if remark else '运单当前尚无备注信息。'
        feedback.addItem(
            title           = '设置或修改备注',
            subtitle        = remark,
            icon            = os.path.abspath('./icon-info.png'),
            valid           = False,
            autocomplete    = 'remark-{}-{} '.format(com_code, post_id)
        )
    feedback.addItem(
        title       = '该运单已被保存，删除运单记录？' if stored else '依然保存运单记录？',
        subtitle    = '保存的运单可方便后续跟踪，查询成功的运单将被自动保存。',
        icon        = os.path.abspath('./icon-del.png' if stored else './icon-save.png'),
        arg         = '{} {} {}'.format('del-post' if stored else 'save-post', com_code, post_id)
    )
    feedback.addItem(item=_fb_return())
    feedback.output()

def showRecommendCompany(recommend_com_codes, post_id):
    feedback = alfred.Feedback()
    recommend_com = []
    for code in recommend_com_codes:
        com = getCompany(code)
        if com:
            recommend_com.append(com)
    # 找到推荐的快递公司
    if recommend_com:
        feedback.addItem(
            title   = '根据运单号找到下列可能的快递公司，请选择：',
            icon    = os.path.abspath('./icon-info.png'),
            valid   = False
        )
        map(lambda c: feedback.addItem(
                title           = c['companyname'],
                subtitle        = c['freginfo'],
                valid           = False,
                autocomplete    = '{} {}'.format(c['code'], post_id)
            ), recommend_com
        )
    # 其它所有快递公司
    feedback.addItem(
        title   = '{}，请在下列中选择：'.format('如果不存在于上述快递公司之中' if recommend_com else '根据运单号没有找到符合的快递公司'),
        icon    = os.path.abspath('./icon-info.png'),
        valid   = False
    )
    for com in getCompany():
        if com in recommend_com:
            continue;
        feedback.addItem(
            title           = com['companyname'],
            subtitle        = com['freginfo'],
            valid           = False,
            autocomplete    = '{} {}'.format(com['code'], post_id)
        )
    feedback.output()

# 根据单号 自动查询
# 1. 查询参数只有一个 则为 运单号
# 2. 查询参数多余一个 则第一个为快递公司名称、缩短名或代码 第二个为运单号
def query():
    arg1 = alfred.argv(1)
    arg2 = alfred.argv(2)
    post_id = arg2 if arg2 else arg1 
    com_codes = arg1 if arg2 else None
    # 如果只有快递单号 没有公司代码 先自动检测获得公司代码
    com_codes = [surmiseCompanyCode(com_codes)] if com_codes is not None else queryCompanyCodeByPostID(post_id)
    if not com_codes:
        alfred.exitWithFeedback(title='没有找到相关的快递信息')
    # 只有一个公司符合 直接给出结果
    if len(com_codes) == 1:
        showSingle(com_codes[0], post_id)
    # 如果有多个 则列出公司列表
    else:
        showRecommendCompany(com_codes, post_id)

# 设置备注
def showRemarkSetting():
    try:
        _, com_code, post_id = alfred.argv(1).split('-')
    except Exception, e:
        alfred.exitWithFeedback(title='参数格式错误。', subtitle='选择返回', valid=False, autocomplete='')
    post = getStoredPost(com_code, post_id)
    if not post:
        alfred.exitWithFeedback(
            title           = '该运单未被保存', 
            subtitle        = '仅可对已保存的运单设置备注，选择查询并尝试保存运单', 
            icon            = os.path.abspath('./icon-error.png'),
            valid           = False, 
            autocomplete    = '{} {}'.format(com_code, post_id)
        )
    remark = ' '.join(sys.argv[2:])
    remark_stored = post.get('remark') if post.get('remark') else '-'
    feedback = alfred.Feedback()
    feedback.addItem(
        title       = '为运单【{} {}】设置或修改备注'.format(getCompany(com_code, 'companyname'), post_id),
        subtitle    = '旧备注: {} 新备注: {}'.format(remark_stored, remark),
        arg         = 'remark-setting {} {} {}'.format(com_code, post_id, remark)
    )
    feedback.addItem(item=_fb_return('{} {}'.format(com_code, post_id)))
    feedback.output()
    
def main():
    cmd = alfred.argv(1)
    # 没有参数 参数存储的运单
    if not cmd:
        return showSaved()
    cmd = cmd.strip().lower()
    # 快递公司列表 以company开始的值都是查询公司列表
    if 'company'.startswith(cmd):
        showCompanyList()
    # 以remark开始的值设置备注
    elif cmd.startswith('remark'):
        showRemarkSetting()
    else:
        query()

if __name__ == '__main__':
    main()