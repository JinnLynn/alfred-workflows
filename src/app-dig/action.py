#!/usr/bin/env python
# -*- coding: utf-8 -*-
#! 强制默认编码为utf-8
import sys
reload(sys)
sys.setdefaultencoding('utf8') 

import os, subprocess, urllib, urllib2, hashlib
import alfred

def setUsername():
    usr = alfred.argv(2)
    if not usr:
        alfred.exit('no username found.')
    config = alfred.Config()
    config.set(username = usr.strip())
    alfred.exit('AppShopper username has setted.')

def openLink():
    link = alfred.argv(2)
    if not link:
        alfred.exit('link missing.')
    subprocess.check_output(['open', link])

def clearCache():
    alfred.cache.clean()
    alfred.exit('All cache cleared.')

def downloadSingle():
    args = alfred.argv(2)
    if not args:
        return
    args = args.split(',')
    if len(args) < 2:
        return
    urllib.urlretrieve(args[0], args[1])

def download():
    links = alfred.argv(2)
    if not links:
        return
    storage_path = os.path.join('/tmp', alfred.bundleID())
    if not os.path.exists(storage_path):
        os.makedirs(storage_path)
    links = links.split(',')
    process = []
    for link in links:
        _, ext = os.path.splitext(link)
        if not ext:
            continue
        filename = '{}{}'.format( hashlib.md5(link).hexdigest(), ext )
        filepath = os.path.join(storage_path, filename)
        if os.path.exists(filepath):
            continue
        sub = subprocess.Popen(
            ['python', 'action.py', 'download-single', '{},{}'.format(link,filepath)], 
            stdin   = subprocess.PIPE, 
            stdout  = subprocess.PIPE, 
            stderr  = subprocess.PIPE
        )
        if sub:
            process.append(sub)
    # 等待所有的下载进程结束
    for sub in process:
        sub.wait()

def toggleAppIconShowing():
    sub = alfred.argv(2)
    if not sub or sub not in ['enable', 'disable']:
        alfred.exit('argument error')
    config = alfred.Config()
    v = True if sub=='enable' else False
    config.set(app_icon_show = v)
    alfred.exit('App Icon Showing {}'.format('Enabled' if v else 'Disabled'))

def main():
    cmd = alfred.argv(1)
    cmd_map = {
        'set-username'      : lambda: setUsername(),
        'open-link'         : lambda: openLink(),
        'clean'             : lambda: clearCache(),
        'download'          : lambda: download(),
        'download-single'   : lambda: downloadSingle(),
        'app-icon-showing'  : lambda: toggleAppIconShowing()
    }
    if not cmd or cmd.lower() not in cmd_map.keys():
        alfred.exit('arguments error.')
    cmd_map[cmd]()

if __name__ == '__main__':
    main()