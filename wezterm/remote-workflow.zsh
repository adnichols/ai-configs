# Managed by ai-configs/wezterm/install.sh.

_ai_configs_herdr_wezterm() {
  local host="$1"
  local launcher='~/.local/bin/herdr-kitty'

  # Preserve Kitty's direct kitten SSH experience when the command is run from
  # Kitty. Everywhere else, open the requested Herdr host in a WezTerm window.
  if [[ -n ${KITTY_WINDOW_ID:-} ]] && (( $+commands[kitten] )); then
    command kitten ssh "$host" -t "$launcher"
  elif (( $+commands[wezterm] )); then
    command wezterm start --always-new-process -- ssh "$host" -t "$launcher"
  else
    print -u2 'herdr launcher: neither wezterm nor kitten is installed'
    return 127
  fi
}

herdr-mbp() { _ai_configs_herdr_wezterm mbp; }
herdr-dever() { _ai_configs_herdr_wezterm dever; }
herdr-mbp14() { _ai_configs_herdr_wezterm mbp14; }

wezterm-remote-help() {
  print -P '%F{cyan}WezTerm remote workflow%f'
  print -P '  %F{green}herdr-mbp%f / %F{green}herdr-dever%f / %F{green}herdr-mbp14%f  open Herdr in a new WezTerm window'
  print -P '  %F{yellow}Cmd+Shift+1/2/3%f                         open mbp/dever/mbp14 directly'
  print -P '  %F{yellow}Cmd+Shift+V%f                             upload a clipboard image and paste its remote path'
}
