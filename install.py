#!/usr/bin/env python
# -*- coding: utf-8 -*-
#! 强制默认编码为utf-8
import sys
reload(sys)
sys.setdefaultencoding('utf8')

import os, json, subprocess, shutil

from pprint import pprint

def die(msg):
    if msg:
        print(msg)
    sys.exit(1)

def getAlfredWorkflowsPath():
    pref_file = os.path.expanduser('~/Library/Preferences/com.runningwithcrayons.Alfred-Preferences.plist')
    try:
        res = subprocess.check_output(['plutil', '-convert', 'json', '-o', '-', pref_file])
        pref = json.loads(res)
    except subprocess.CalledProcessError, e:
        die('Load alfred preferrnces fail')
    except:
        die('parse alfred preferrnces fail')
    if int(pref['version'].split('.')[0]) < 2:
        die('Alfred version must greater than 2, current: {}'.format(pref['version']))
    workflows_path = os.path.expanduser('~/Library/Application Support/Alfred 2/Alfred.alfredpreferences/workflows')
    if pref.has_key('syncfolder'):
        syncfolder = os.path.expanduser(pref['syncfolder'])
        workflows_path = os.path.join(syncfolder, 'Alfred.alfredpreferences/workflows')
    if not os.path.exists(workflows_path):
        die('Alfred workflows path is non-existent.')
    return workflows_path

def run():
    workflows_path = getAlfredWorkflowsPath()
    src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
    for dirname in os.listdir(src_path):
        abs_path = os.path.join(src_path, dirname)
        if not os.path.isdir(abs_path):
            continue
        link_dirname = 'net.jeeker.awf.{}'.format(dirname)
        link_path = os.path.join(workflows_path, link_dirname)
        if os.path.exists(link_path):
            if os.path.islink(link_path): 
                if os.readlink(link_path) == abs_path:
                    print('workflow alread exists: {}'.format(link_dirname))
                    continue
                else:
                    os.remove(link_path)
            elif os.path.isfile(link_path):
                    os.remove(link_path)
            else:
                shutil.rmtree(link_path)
        os.symlink(abs_path, link_path)
        print('new workflows added: {}'.format(link_dirname))

if __name__ == '__main__':
    run()