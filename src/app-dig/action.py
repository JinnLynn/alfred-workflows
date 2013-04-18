#!/usr/bin/env python
# -*- coding: utf-8 -*-
#! 强制默认编码为utf-8
import sys
reload(sys)
sys.setdefaultencoding('utf8') 

import os, subprocess, urllib, urllib2, hashlib
import alfred

from app import country_currency

def setUsername():
    usr = alfred.argv(2)
    if not usr:
        alfred.exit('no username found.')
    alfred.config.set(username = usr.strip())
    alfred.exit('AppShopper username has setted.')

def openLink():
    link = alfred.argv(2)
    if not link:
        alfred.exit('link missing.')
    subprocess.check_output(['open', link])

def clearCache():
    alfred.cache.clean()
    alfred.exit('All cache cleared.')

def toggleAppIconShowing():
    sub = alfred.argv(2)
    if not sub or sub not in ['enable', 'disable']:
        alfred.exit('argument error')
    v = True if sub=='enable' else False
    alfred.config.set(app_icon_show = v)
    alfred.exit('App Icon Showing {}'.format('Enabled' if v else 'Disabled'))

def changeCountry():
    sub = alfred.argv(2)
    if not sub or sub not in country_currency.keys():
        return
    alfred.config.set(country=sub)
    alfred.cache.clean()
    alfred.exit('Country/Currency has changed to {}.'.format(country_currency[sub]))

def main():
    cmd = alfred.argv(1)
    cmd_map = {
        'set-username'      : lambda: setUsername(),
        'open-link'         : lambda: openLink(),
        'clean'             : lambda: clearCache(),
        'app-icon-showing'  : lambda: toggleAppIconShowing(),
        'change-country'    : lambda: changeCountry()
    }
    if not cmd or cmd.lower() not in cmd_map.keys():
        alfred.exit()
    cmd_map[cmd]()

if __name__ == '__main__':
    main()