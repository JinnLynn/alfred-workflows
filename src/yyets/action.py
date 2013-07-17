# -*- coding: utf-8 -*-
import alfred
alfred.setDefaultEncodingUTF8()

import base64
import subprocess
from AppKit import NSPasteboard, NSArray

# 拷贝到剪切板
def copyToClipboard(word):
    pb = NSPasteboard.generalPasteboard()
    pb.clearContents()
    a = NSArray.arrayWithObject_(word)
    pb.writeObjects_(a)

def main():
    cmd = alfred.argv(1)
    try:
        links = base64.b64decode(alfred.argv(2)).split(',')
        page = links[0]
        emule = links[1]
        magnet = links[2]
    except Exception, e:
        alfred.exit('出错啦')
    if cmd == 'today-copy-emule':
        if not emule:
            alfred.exit('没有电驴地址')
        copyToClipboard(emule)
        alfred.exit('电驴地址已拷贝到剪切板')
    elif cmd == 'today-copy-magnet':
        if not magnet:
            alfred.exit('没有磁力链地址')
        copyToClipboard(magnet)
        alfred.exit('磁力链地址已拷贝到剪切板')
    elif cmd == 'today-open-ds':
        # 优先使用emule
        l = emule if emule else magnet
        if not l:
            alfred.exit('没有下载链接')
        alfred.query('ds create {}'.format(emule))
    elif cmd == 'today-open-page':
        if not page:
            alfred.exit('没有页面地址')
        subprocess.check_output('open "{}"'.format(page), shell=True)
    else:
        alfred.exit('出错啦')

if __name__ == '__main__':
    main()