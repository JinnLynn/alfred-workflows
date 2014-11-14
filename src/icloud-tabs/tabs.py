#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os, sys
import subprocess
import plistlib
from datetime import datetime, tzinfo, timedelta
import time

import alfred
alfred.setDefaultEncodingUTF8()

__version__ = '1.0.0'

class LocalTZ(tzinfo):
    def utcoffset(self, dt):
        return timedelta(seconds=-time.timezone)
    def dst(self, dt):
        return timedelta(0)

class UTC(tzinfo):
    def utcoffset(self, dt):
        return timedelta(0)
    def dst(self, dt):
        return timedelta(0)

@alfred.cached('icloud-tabs', _expire=5)
def accessTabs():
    try:
        res = subprocess.check_output('plutil -convert xml1 ~/Library/SyncedPreferences/com.apple.Safari.plist -o -', shell=True)
        data = plistlib.readPlistFromString(res)
        del data['versionid']
        for k in data.get('values', {}):
            del data['values'][k]['remotevalue']
            lm = data['values'][k]['value']['LastModified']
            lm = lm.replace(tzinfo=UTC()).astimezone(LocalTZ())
            data['values'][k]['value']['LastModified'] = lm.strftime('%Y-%m-%d %H:%M')
    except Exception, e:
        return None
    return data

def showDevices():
    data = accessTabs()
    feedback = alfred.Feedback()
    for k in data['values'].keys():
        d = data['values'][k]['value']
        tabs_count = len(d.get('Tabs', {}))
        feedback.addItem(
            title           = d['DeviceName'],
            subtitle        = '{} tabs. last modified: {}'.format(tabs_count, d['LastModified']),
            valid           = False,
            autocomplete    = d['DeviceName']
        )
    feedback.output()

def showTabsByDevice(device_name):
    data = accessTabs()
    feedback = alfred.Feedback()
    for k in data['values'].keys():
        d = data['values'][k]['value']
        if not d['DeviceName'].lower().startswith(device_name.lower()):
            continue
        tabs_count = len(d.get('Tabs', {}))
        feedback.addItem(
            title       = d['DeviceName'],
            subtitle    = '{} tabs. last modified: {}'.format(tabs_count, d['LastModified']),
            valid       = False
        )
        for tab in d.get('Tabs', {}):
            feedback.addItem(
                title       = tab['Title'],
                subtitle    = tab['URL'],
                icon        = 'icon-tabs.png',
                arg         = tab['URL']
            )
    if feedback.isEmpty():
        alfred.exitWithFeedback(title="Oops! Nothing found.", valid=False)
    feedback.output()

def main():
    try:
        device = alfred.argv(1)
        data = accessTabs()
        if not data or not data.get('values'):
            alfred.exitWithFeedback(title="Oops! iCloud Tabs non-existend", valid=False)
        if device:
            showTabsByDevice(device)
        else:
            showDevices()
    except Exception, e:
        alfred.exitWithFeedback(title='Oops! {}'.format(e))

if __name__ == '__main__':
    main()