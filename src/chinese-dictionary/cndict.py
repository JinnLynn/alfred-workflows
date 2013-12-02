#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os, sys, json, time
from pprint import pprint

import alfred
alfred.setDefaultEncodingUTF8()

__version__ = '2.0.0'

_api_url = 'http://fanyi.youdao.com/openapi.do'
_api_version = '1.1'
_api_keyfrom = 'awf-Chinese-Dict'
_api_key = '19965805'

_error_desc = {
    20 : '要翻译的文本过长。',
    30 : '无法进行有效的翻译。',
    40 : '不支持的语言类型。',
    50 : '无效的key。'
}

def fetchData(q):
    cache_name = 'youdao-fanyi-{}'.format(q)
    cache = alfred.cache.get(cache_name)
    if cache:
        return cache
    try:
        req = alfred.request.get(
            _api_url,
            data = {
                'keyfrom'   : _api_keyfrom,
                'key'       : _api_key,
                'version'   : _api_version, 
                'type'      : 'data' ,
                'doctype'   : 'json',
                'q'         : q
            }
        )
        data = json.loads( req.getContent() )
        if data:
            alfred.cache.set(cache_name, data, 3600*24)
            return data
    except Exception, e:
        pass

def isEnglish(w):
    for i in w:
        if ord(i) > 127:
            return False
    return True

# 清理解释
# 有道的解释可能出现如 [试验] test
# 清理[]的内容
def clearExplain(e):
    i = e.rfind(']')
    if i >= 0:
        return e[i+1:].strip()
    return e.strip()

def query():
    tryCleanCache()
    w = ' '.join(sys.argv[1:]).strip()
    try:
        ret = fetchData(w)
        if not ret:
            raise Exception('服务器访问失败。')
        # pprint(ret)
        if ret.get('errorCode', -1) != 0:
            error_msg = _error_desc.get(ret.get('errorCode', -1))
            raise Exception(error_msg if error_msg else '未知错误。' )
        is_eng = isEnglish(w)
        feedback = alfred.Feedback()
        # 有解释
        basic = ret.get('basic', {})
        phonetic = basic.get('phonetic', '')
        feedback.addItem(
            title       = '{} {}'.format(w, '[{}]'.format(phonetic) if phonetic else ''),
            subtitle    = '译: {}'.format('; '.join(ret.get('translation', []))),
            arg         = w
        )
        for e in basic.get('explains', []):
            feedback.addItem(
                title = e,
                autocomplete = None if is_eng else clearExplain(e),
                valid = False
            )
        # 网络释义
        web = ret.get('web', [])
        if web:
            feedback.addItem(title='--- 网络释义 ---', valid=False,)
            for w in web:
                feedback.addItem(
                    title       = w.get('key'),
                    subtitle    = '; '.join(w.get('value')),
                    valid       = False,
                    autocomplete = w.get('key')
                )
        feedback.output()
    except Exception, e:
        alfred.exitWithFeedback(title=w, subtitle='出错了，{}'.format(e), valid=False)

def tryCleanCache():
    if alfred.cache.get('cache-cleaned'):
        return
    alfred.cache.cleanExpired()
    alfred.cache.set('cache-cleaned', True, 3600*24)


if __name__ == '__main__':
    query()