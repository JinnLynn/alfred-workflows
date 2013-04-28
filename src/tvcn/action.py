#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys

import alfred

from tvcn import getFavChannels, isChannelFaved, getChannelTitle

def toggleFavChannel():
    channel = alfred.argv(2)
    channel_title = getChannelTitle(channel)
    if not channel_title:
        return
    favs = getFavChannels()
    if isChannelFaved(channel):
        favs = filter(lambda f: f!=channel, favs)
        alfred.config.set(fav=favs)
        alfred.exit('频道 {} 已被取消收藏'.format(channel_title))
    else:
        favs.append(channel)
        alfred.config.set(fav=favs)
        alfred.exit('已收藏频道 {}'.format(channel_title))

def main():
    cmd_map = {
        'toggle-fav'    : lambda: toggleFavChannel()
    }
    cmd = alfred.argv(1)
    if not cmd or cmd.lower() not in cmd_map.keys():
        return
    cmd_map[cmd.lower()]()

if __name__ == '__main__':
    main()
