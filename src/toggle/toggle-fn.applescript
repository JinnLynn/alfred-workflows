-- FROM: http://www.alfredforum.com/topic/1849-toggle-fn-key-behavior/
tell application "System Preferences"
    set current pane to pane id "com.apple.preference.keyboard"
    tell application "System Events"
        tell process "System Preferences"
            click checkbox "Use all F1, F2, etc. keys as standard function keys" of tab group 1 of window "Keyboard"
        end tell
    end tell
    quit
end tell