#!/usr/bin/env python
# -*- coding: utf-8 -*-
#! 强制默认编码为utf-8
import sys
reload(sys)
sys.setdefaultencoding('utf8')

import os, json, subprocess, shutil

def exit(msg, retcode=0):
    if msg:
        print(msg)
    sys.exit(retcode)

def die(msg):
    eixt(msg, 1)

def rmAny(path):
    if os.path.isfile(path) or os.path.islink(path):
        os.remove(path)
    elif os.path.isdir(path):
        shutil.rmtree(path)

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

def main():
    prefix = 'net.jeeker.awf'
    workflows_path = getAlfredWorkflowsPath()
    base_path = os.path.dirname(os.path.abspath(__file__))
    src_path = os.path.join(base_path, 'src')

    subcmd = ''
    if len(sys.argv)>=2:
        subcmd = sys.argv[1].lower()
        if subcmd not in ['remove', 'clean']:
            exit('argument error.')

    if subcmd == 'clean':
        clean_cmd = "cd {} && find . \( -name '*.pyc' -o -name 'log.txt' \) -exec rm {} \;".format(base_path, '{}')
        subprocess.check_output(clean_cmd, shell=True)
        exit('everything is clean.')

    # 删除所有旧的链接
    for dirname in os.listdir(workflows_path):
        if dirname.startswith(prefix):
            rmAny(os.path.join(workflows_path, dirname))

    if subcmd == 'remove':
        exit('all workflows removed.')

    # 重新链接
    for dirname in os.listdir(src_path):
        abs_path = os.path.join(src_path, dirname)
        if not os.path.isdir(abs_path):
            continue
        link_dirname = '{}.{}'.format(prefix, dirname)
        link_path = os.path.join(workflows_path, link_dirname)
        os.symlink(abs_path, link_path)
        print('new workflows added: {}'.format(link_dirname))

if __name__ == '__main__':
    main()