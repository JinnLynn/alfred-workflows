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
    if [[ "$status" = "FALSE" ]]; then
        defaults write com.apple.finder AppleShowAllFiles TRUE
        killall Finder
        echo "Success, 'hidden' files are showing."
    else
        defaults write com.apple.finder AppleShowAllFiles FALSE
        killall Finder
        echo "Success, 'hidden' files are hiding."
    fi
}

