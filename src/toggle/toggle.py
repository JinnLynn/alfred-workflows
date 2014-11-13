#!/usr/bin/env python
# -*- coding: utf-8 -*-
#! 强制默认编码为utf-8
import sys
reload(sys)
sys.setdefaultencoding('utf8') 

import objc, subprocess
import alfred

__version__ = '1.0.0'

TOGGLES = [
    {
        'arg'       : 'wifi',
        'title'     : 'Toggle WIFI Enable/Disable',
        'cmd'       : lambda: doShellScript('. toggle.sh && toggle_wifi'),
        'icon'      : 'icons/wifi.png'
    },
    {
        'arg'       : 'bluetooth',
        'title'     : 'Toggle Bluetooth Enable/Disable',
        'cmd'       : lambda: toggleBluetooth(),
        'icon'      : 'icons/bluetooth.png'
    },
    {
        'arg'       : 'hidden-files',
        'title'     : 'Toggle Hidden Files Show/Hide',
        'cmd'       : lambda: doShellScript('. toggle.sh && toggle_hidden_files')
    },
    {
        'arg'       : 'desktop-icons',
        'title'     : 'Toggle Desktop Icons Show/Hide',
        'cmd'       : lambda: doShellScript('. toggle.sh && toggle_desktop_icons')
    },
    {
        'arg'       : 'fn',
        'title'     : 'Toggle fn Key Behavior',
        'cmd'       : lambda: doShellScript('. toggle.sh && toggle_fn')
    }
]

def doShellScript(script):
    res = subprocess.check_output(script, shell=True)
    alfred.exit(res.strip())
    
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

def main():
    cmd = alfred.argv(1)
    for toggle in TOGGLES:
        if toggle['arg'] == cmd:
            return toggle['cmd']()

    feedback = alfred.Feedback()
    for toggle in TOGGLES:
        feedback.addItem(**toggle)
    feedback.output()

if __name__ == '__main__':
    main()