#!/usr/bin/env bash

function toggle_wifi {
    device=$(networksetup -listallhardwareports | grep -A 2 -E "AirPort|Wi-Fi" | grep -m 1 -o -e en[0-9])

    if [[ -z "$(networksetup -getairportpower $device | grep On)" ]]; then
        networksetup -setairportpower $device On && echo "WIFI Enabled."
    else
        networksetup -setairportpower $device Off && echo "WIFI Disabled."
    fi
}

function toggle_hidden_files {
    status=$(defaults read com.apple.finder AppleShowAllFiles)
    if [[ $status = 1 ]]; then
        defaults write com.apple.finder AppleShowAllFiles -bool false
        killall Finder
        echo "Success, 'hidden' files are hiding."
    else
        defaults write com.apple.finder AppleShowAllFiles -bool true
        killall Finder
        echo "Success, 'hidden' files are showing."
    fi
}

function toggle_desktop_icons {
    status=$(defaults read com.apple.finder CreateDesktop)
    if [[ $status = 1 ]]; then
        defaults write com.apple.finder CreateDesktop -bool false
        killall Finder
        echo "Success, all desktop icons are hiding."
    else
        defaults write com.apple.finder CreateDesktop -bool true
        killall Finder
        echo "Success, all desktop icons are showing."
    fi
}

function toggle_fn {
    osascript toggle-fn.applescript && echo "Function key behavior toggled"
}
