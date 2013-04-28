#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os, subprocess, urllib, urllib2, hashlib

import alfred
alfred.setDefaultEncodingUTF8()

from app import country_currency

def setUsername():
    usr = alfred.argv(2)
    if not usr:
        alfred.exit('no username found.')
    alfred.config.set(username = usr.strip())
    alfred.exit('AppShopper username has setted.')

def openLink():
    try:
        links = alfred.argv(2).strip().split(',')
        open_store_link = alfred.config.get('open_store_link', True)
        link = links[0] if open_store_link else links[1]
        subprocess.check_output(['open', link])
    except Exception, e:
        alfred.exit('something error.')

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

def switchLinkOpenType():
    alfred.cache.clean()
    open_store_link = alfred.config.get('open_store_link', True)
    new_value = False if open_store_link else True
    alfred.config.set(open_store_link=new_value)
    alfred.exit('{} link will be opened.'.format('iTunes' if new_value else 'AppShopper'))


def main():
    cmd = alfred.argv(1)
    cmd_map = {
        'set-username'      : lambda: setUsername(),
        'open-link'         : lambda: openLink(),
        'clean'             : lambda: clearCache(),
        'app-icon-showing'  : lambda: toggleAppIconShowing(),
        'change-country'    : lambda: changeCountry(),
        'switch-link-open-type' : lambda: switchLinkOpenType()
    }
    if not cmd or cmd.lower() not in cmd_map.keys():
        alfred.exit()
    cmd_map[cmd]()

if __name__ == '__main__':
    main()