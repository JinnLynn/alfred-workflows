#!/usr/bin/env python
# -*- coding: utf-8 -*-
#! 强制默认编码为utf-8
import sys
reload(sys)
sys.setdefaultencoding('utf8') 

import objc, subprocess

import alfred

def run():
    cmd_map = {
        'list'          : lambda: showList(),
        'wifi'          : lambda: toggleWIFI(),
        'bluetooth'     : lambda: toggleBluetooth(),
        'hidden'        : lambda: toggleHiddenFiles(),
        'desktop-icons' : lambda: toggleDesktopIcons()
    }

    cmd = alfred.argv(1)
    if cmd is None or cmd not in cmd_map.keys():
        cmd = 'list'
    cmd_map[cmd]()

def showList():
    feedback = alfred.Feedback()
    feedback.addItem(
        title   = 'Toggle WIFI',
        arg     = 'wifi',
        icon    = 'icons/wifi.png'
        ),
    feedback.addItem(
        title   = 'Toggle Bluetooth',
        arg     = 'bluetooth',
        icon    = 'icons/bluetooth.png'
        ),
    feedback.addItem(
        title   = 'Toggle Hidden Files Show/Hide',
        arg     = 'hidden'
        ),
    feedback.addItem(
        title   = 'Toggle Desktop Icons Show/Hide',
        arg     = 'desktop-icons'
        )
    feedback.output()

def doShellScript(script):
    res = subprocess.check_output(script, shell=True)
    alfred.exit(res.strip())

def toggleWIFI():
    doShellScript('. toggle.sh && toggle_wifi')
    
# base from "http://web.mac.com/nissplus/IslandOfApples/Enable%20Disable%20Mac%20OSX%20Bluetooth%20from%20Python.html"
def toggleBluetooth():
    bundle = objc.loadBundle('IOBluetooth', globals(), bundle_path=objc.pathForFramework('/System/Library/Frameworks/IOBluetooth.framework'))
    if not bundle:
        alfred.exit('Toggle Bluetooth fail. initFrameworkWrapper error')
    fs = [('IOBluetoothPreferenceGetControllerPowerState', 'oI'),('IOBluetoothPreferenceSetControllerPowerState','vI')]
    ds = {}
    objc.loadBundleFunctions(bundle, ds, fs)
    for (name, handle) in fs:
        if not name in ds:
            alfred.exit('Toggle Bluetooth fail. failed to load: {}'.format(name))
    if ds['IOBluetoothPreferenceGetControllerPowerState']() == 1:
        ds['IOBluetoothPreferenceSetControllerPowerState'](0)
        alfred.exit('Bluetooth Disabled.')
    else:
        ds['IOBluetoothPreferenceSetControllerPowerState'](1)
        alfred.exit('Bluetooth Enable.')

def toggleHiddenFiles():
    doShellScript('. toggle.sh && toggle_hidden_files')

def toggleDesktopIcons():
    doShellScript('. toggle.sh && toggle_desktop_icons')

if __name__ == '__main__':
    run()