-- Pandoc's gfm reader passes raw HTML through (and `-raw_html` does not stop it), so a spec line such as
-- `/assets/<rev>/` would reach Ava as a tag and be stripped. Render raw HTML as the text the author wrote.
function RawInline(el)
  if el.format:match("html") then return pandoc.Str(el.text) end
end

function RawBlock(el)
  if el.format:match("html") then return pandoc.Para({pandoc.Str(el.text)}) end
end
