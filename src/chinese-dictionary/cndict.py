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

@alfred.cached('cache-cleaned')
def tryCleanCache():
    alfred.cache.cleanExpired()
    return True

def fetchData(q):
    cache_name = 'youdao-fanyi-{}'.format(q.lower().replace(' ', '_'))
    @alfred.cached(cache_name, _set_check=lambda d: isinstance(d, dict) and d.get('errorCode', -1) == 0)
    def _fetch():
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
            return json.loads( req.getContent() )
        except Exception, e:
            pass
    return _fetch()

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

def translate(w):
    ret = fetchData(w)
    if not ret:
        raise Exception('服务器访问失败。')
    # pprint(ret)
    if ret.get('errorCode', -1) != 0:
        error_msg = _error_desc.get(ret.get('errorCode', -1))
        raise Exception(error_msg if error_msg else '未知错误。' )
    return ret

def query():
    tryCleanCache()
    w = ' '.join(sys.argv[1:]).strip()
    try:
        ret = translate(w)
        is_eng = isEnglish(w)
        feedback = alfred.Feedback()
        translation = ret.get('translation', [])
        # 基本解释
        basic = ret.get('basic', {})
        phonetic = basic.get('phonetic')
        us_phonetic = basic.get('us-phonetic')
        uk_phonetic = basic.get('uk-phonetic')
        ph_out = []
        us_phonetic and ph_out.append('美[{}]'.format(us_phonetic))
        uk_phonetic and ph_out.append('英[{}]'.format(uk_phonetic))
        if not ph_out and phonetic:
            ph_out.append('[{}]'.format(phonetic))
        feedback.addItem(
            title       = ' '.join(ph_out) if ph_out else w,
            subtitle    = '译: {}'.format('; '.join(translation)) if translation else '',
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

if __name__ == '__main__':
    query()