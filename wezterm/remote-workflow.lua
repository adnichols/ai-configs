-- Managed by ai-configs/wezterm/install.sh.
--
-- Decorate Herdr tabs using the title emitted by herdr-kitty-status while
-- retaining terminal-agnostic title updates from the remote Herdr plugin.
local M = {}

local HOST_COLORS = {
  mbp = { background = '#3B2E5A', foreground = '#F0EAF7' },
  dever = { background = '#1E3A5F', foreground = '#E6EDF3' },
  mbp14 = { background = '#244436', foreground = '#E6F2EA' },
  ['mbp14-2'] = { background = '#244436', foreground = '#E6F2EA' },
}

local STATUS_COLORS = {
  working = '#F9E2AF',
  blocked = '#FAB387',
  done = '#A6E3A1',
}

local function configured_host(host)
  if not host then
    return nil
  end

  host = host:lower()
  host = host:gsub('^SSH[MUX]*:', '')
  return HOST_COLORS[host] and host or nil
end

local function parse_ssh_host(argv)
  local options_with_value = {
    ['-b'] = true, ['-c'] = true, ['-D'] = true, ['-E'] = true,
    ['-F'] = true, ['-I'] = true, ['-i'] = true, ['-J'] = true,
    ['-L'] = true, ['-l'] = true, ['-m'] = true, ['-O'] = true,
    ['-o'] = true, ['-p'] = true, ['-Q'] = true, ['-R'] = true,
    ['-S'] = true, ['-W'] = true, ['-w'] = true,
  }

  local index = 1
  while argv and index <= #argv do
    local argument = argv[index]
    if argument == '--' then
      return configured_host(argv[index + 1])
    end
    if options_with_value[argument] then
      index = index + 2
    elseif argument:match('^-o.+') or argument:match('^-p.+') or argument:match('^-l.+') then
      index = index + 1
    elseif argument:sub(1, 1) == '-' then
      index = index + 1
    else
      return configured_host(argument)
    end
  end
end

function M.parse_status_title(title)
  local prefix, working, blocked, done, trailing = tostring(title):match(
    '^(.-)%s+(%d+)%s*/%s*(%d+)%s*/%s*(%d+)(.*)$'
  )
  if not prefix then
    return nil
  end

  local host = prefix:match('^Herdr%s+%(([^)]+)%)$')
  host = configured_host(host)
  if not host then
    return nil
  end

  -- The optional suffix transports colors to Kitty. WezTerm uses the
  -- user-selected host palette above, so it deliberately strips this metadata.
  if trailing ~= '' and not trailing:match('^%s+%[herdr%-kitty') then
    return nil
  end

  return {
    host = host,
    label = prefix,
    working = working,
    blocked = blocked,
    done = done,
    colors = HOST_COLORS[host],
  }
end

function M.host_for_pane(pane)
  local from_title = M.parse_status_title(pane:get_title())
  if from_title then
    return from_title.host
  end

  local from_domain = configured_host(pane:get_domain_name())
  if from_domain then
    return from_domain
  end

  local process = pane:get_foreground_process_info()
  if process and process.argv then
    return parse_ssh_host(process.argv)
  end
end

function M.format_tab_title(wezterm, tab, max_width)
  local title = tab.tab_title
  if not title or #title == 0 then
    title = tab.active_pane.title
  end

  local status = M.parse_status_title(title)
  if not status then
    local width = math.max((max_width or 24) - 2, 1)
    return { { Text = ' ' .. wezterm.truncate_right(title, width) .. ' ' } }
  end

  local colors = status.colors
  -- Paint every Herdr tab with its host color. The status title remains text,
  -- so the live counts keep updating without a terminal-specific renderer.
  return {
    { Background = { Color = colors.background } },
    { Foreground = { Color = colors.foreground } },
    { Text = ' ' .. status.label .. ' ' },
    { Foreground = { Color = STATUS_COLORS.working } },
    { Text = status.working },
    { Foreground = { Color = colors.foreground } },
    { Text = ' / ' },
    { Foreground = { Color = STATUS_COLORS.blocked } },
    { Text = status.blocked },
    { Foreground = { Color = colors.foreground } },
    { Text = ' / ' },
    { Foreground = { Color = STATUS_COLORS.done } },
    { Text = status.done .. ' ' },
  }
end

local function append_key(config, key)
  config.keys = config.keys or {}
  for _, existing in ipairs(config.keys) do
    if existing.key == key.key and existing.mods == key.mods then
      return
    end
  end
  table.insert(config.keys, key)
end

local function append_launch_menu(config, entry)
  config.launch_menu = config.launch_menu or {}
  for _, existing in ipairs(config.launch_menu) do
    if existing.label == entry.label then
      return
    end
  end
  table.insert(config.launch_menu, entry)
end

local function herdr_command(host)
  return { 'ssh', host, '-t', '~/.local/bin/herdr-kitty' }
end

function M.apply(config, wezterm)
  config.use_fancy_tab_bar = false
  -- The retro bar defaults to 16 cells, which truncates `Herdr (mbp14-2)`
  -- before its working / blocked / done counters.
  config.tab_max_width = 36
  config.show_tab_index_in_tab_bar = false
  config.show_new_tab_button_in_tab_bar = true
  config.hide_tab_bar_if_only_one_tab = false

  append_launch_menu(config, { label = 'Herdr · mbp', args = herdr_command('mbp') })
  append_launch_menu(config, { label = 'Herdr · dever', args = herdr_command('dever') })
  append_launch_menu(config, { label = 'Herdr · mbp14', args = herdr_command('mbp14') })

  append_key(config, {
    key = '1', mods = 'CMD|SHIFT',
    action = wezterm.action.SpawnCommandInNewWindow { args = herdr_command('mbp') },
  })
  append_key(config, {
    key = '2', mods = 'CMD|SHIFT',
    action = wezterm.action.SpawnCommandInNewWindow { args = herdr_command('dever') },
  })
  append_key(config, {
    key = '3', mods = 'CMD|SHIFT',
    action = wezterm.action.SpawnCommandInNewWindow { args = herdr_command('mbp14') },
  })
  append_key(config, {
    key = '[', mods = 'OPT', action = wezterm.action.SendString '\x1b[27;3;91~',
  })
  append_key(config, {
    key = ']', mods = 'OPT', action = wezterm.action.SendString '\x1b[27;3;93~',
  })
  append_key(config, {
    key = 'v', mods = 'CMD|SHIFT',
    action = wezterm.action_callback(function(window, pane)
      local host = M.host_for_pane(pane)
      if not host then
        window:toast_notification(
          'WezTerm image paste',
          'Focus a Herdr or SSH pane for mbp, dever, or mbp14 before pasting an image.',
          nil,
          5000
        )
        return
      end

      wezterm.background_child_process {
        wezterm.home_dir .. '/.local/bin/wezterm-paste-image-to-ssh',
        '--host', host,
        '--pane-id', tostring(pane:pane_id()),
      }
    end),
  })

  wezterm.on('format-tab-title', function(tab, _, _, _, _, max_width)
    return M.format_tab_title(wezterm, tab, max_width)
  end)
end

return M
