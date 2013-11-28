# -*- coding: utf-8 -*-
import subprocess
from base64 import b64decode

import alfred
alfred.setDefaultEncodingUTF8()

import express

# 打开地址
#! 地址在传递参数中均使用base64编码 防止出错 
def openURL():
    try:
        page = b64decode(alfred.argv(2))
        subprocess.check_output('open "{}"'.format(page), shell=True)
    except Exception, e:
        alfred.log(e)
        alfred.exit('出错啦')

# 运单的保存与删除
def postRecord(to_save):
    com_code = alfred.argv(2)
    post_id = alfred.argv(3)
    if com_code is None or post_id is None:
        alfred.exit('出错了，参数错误。')
    if to_save:
        express.savePost(com_code, post_id)
    else:
        express.delPost(com_code, post_id)
    alfred.exit('运单 {} 已{}'.format(post_id, '保存' if to_save else '删除'))

def main():
    cmds = {
        'open-url'  : lambda: openURL(),
        'save-post' : lambda: postRecord(True),
        'del-post'  : lambda: postRecord(False)
    }
    cmd = alfred.argv(1)
    if not cmd or cmd.lower() not in cmds.keys():
        alfred.exit('出错啦')
    cmds[cmd]();

if __name__ == '__main__':
    main()