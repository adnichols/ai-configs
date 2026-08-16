-- Cmd+Shift+V uploads the current local clipboard image to both coding hosts
-- only when a supported terminal application is focused. In every other app,
-- the original key event is passed through unchanged.
--
-- Kitty and WezTerm are intentionally excluded: each already owns
-- Cmd+Shift+V with a host-aware paste helper. Intercepting those apps caused
-- the OS-level dual-host uploader to win, so the terminal-native path never
-- ran and remote Pi sessions could end up with a local Mac clipboard path.
local remoteImagePaste = os.getenv("HOME") .. "/.local/bin/remote-image-paste"
local imagePasteRunning = false
local terminalBundleIDs = {
  ["com.apple.Terminal"] = true,
  ["com.googlecode.iterm2"] = true,
  ["com.mitchellh.ghostty"] = true,
  -- Kitty/WezTerm handle Cmd+Shift+V themselves (host-aware clipssh helpers).
}

local function frontmostTerminal()
  local app = hs.application.frontmostApplication()
  return app and terminalBundleIDs[app:bundleID()]
end

local function startImagePaste()
  if imagePasteRunning then
    hs.alert.show("Remote image upload is already running", 1)
    return
  end

  imagePasteRunning = true
  hs.alert.show("Uploading image to dever and mbp…", 1)

  local task = hs.task.new(remoteImagePaste, function(exitCode, stdout, stderr)
    imagePasteRunning = false
    if exitCode == 0 then
      -- The helper writes the shared remote file path to the local clipboard.
      -- Focus may have changed while the upload ran, so never inject text into
      -- a non-terminal application. The path remains available for normal paste.
      if frontmostTerminal() then
        hs.eventtap.keyStroke({ "cmd" }, "v", 0)
      else
        hs.alert.show("Image uploaded; paste its path from the clipboard in a terminal", 4)
      end
    else
      local detail = stderr:gsub("%s+$", "")
      hs.alert.show(detail ~= "" and detail or "Remote image upload failed", 4)
    end
  end)

  if task then
    task:start()
  else
    imagePasteRunning = false
    hs.alert.show("Could not start remote-image-paste", 4)
  end
end

-- Keep this global reference alive for the duration of the Hammerspoon session.
remoteImagePasteTap = hs.eventtap.new({ hs.eventtap.event.types.keyDown }, function(event)
  local flags = event:getFlags()
  if event:getKeyCode() ~= hs.keycodes.map.v
      or not flags.cmd or not flags.shift
      or flags.ctrl or flags.alt then
    return false
  end

  if not frontmostTerminal() then
    return false
  end

  startImagePaste()
  return true
end)
remoteImagePasteTap:start()
