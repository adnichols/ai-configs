# Managed by ai-configs/kitty/install.sh.
alias kssh='kitten ssh'
alias herdr-mbp='kitten ssh mbp -t /Users/anichols/.local/bin/herdr-kitty'
alias herdr-dever='kitten ssh dever -t /home/anichols/.local/bin/herdr-kitty'

kitty-remote-help() {
  print -P '%F{cyan}Kitty remote workflow%f'
  print -P '  %F{green}herdr-mbp%f / %F{green}herdr-dever%f  open Herdr directly'
  print -P '  %F{green}mosh mbp%f or %F{green}mosh dever%f, then run %F{green}herdr%f remotely'
  print -P '  %F{yellow}Cmd+Shift+V%f              upload a clipboard image and paste its path'
  print -P '  Run %F{green}kitty-remote-help%f to show this reminder again.\n'
}

if [[ -o interactive && -n ${KITTY_WINDOW_ID:-} && -z ${SSH_CONNECTION:-} ]]; then
  kitty-remote-help
fi
