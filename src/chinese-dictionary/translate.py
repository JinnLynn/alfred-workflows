#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os, sys, json, time
from pprint import pprint

import alfred
alfred.setDefaultEncodingUTF8()

import cndict

def main():
    try:
        w = ' '.join(sys.argv[1:]).strip()
        ret = cndict.translate(w)
        translation = ret.get('translation', [])
        translation = ';'.join(translation) if translation else ''
        phonetic = ret.get('basic', {}).get('phonetic')
        if not translation:
            raise Exception('无法翻译')
        if phonetic:
            print('[{}]'.format(phonetic))
        print(translation)
    except Exception, e:
        alfred.exit('出错了，{}'.format(e), 1)

if __name__ == '__main__':
    main()
