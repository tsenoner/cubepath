--- Callout box filter for pandoc.
--- Transforms fenced divs (.algorithm, .tip, .caution, .info) into styled
--- blocks for typst output. HTML output uses CSS classes directly.
--- Also handles image rotation and algorithm trigger color spans.

local callout_styles = {
  algorithm = {
    label = "Algorithm",
    bg = "e8f4fd",
    border = "2196F3",
    text = "1565C0",
  },
  tip = {
    label = "Tip",
    bg = "e8f5e9",
    border = "4CAF50",
    text = "2E7D32",
  },
  caution = {
    label = "Caution",
    bg = "fff3e0",
    border = "FF9800",
    text = "E65100",
  },
  info = {
    label = "Info",
    bg = "f5f5f5",
    border = "9E9E9E",
    text = "616161",
  },
}

local trigger_colors = {
  ["trig-r"] = { hex = "D32F2F" },  -- Red: R U R' U' family
  ["trig-g"] = { hex = "2E7D32" },  -- Green: R U R' U family
  ["trig-b"] = { hex = "1565C0" },  -- Blue: R' F R F' family
}

function Image(el)
  local angle = el.attributes["rotate"]
  if not angle then return end
  el.attributes["rotate"] = nil  -- don't pass through
  if FORMAT:match("typst") then
    local w = el.attributes["width"] or ""
    el.attributes["width"] = nil
    local src = el.src
    local img = w ~= ""
      and string.format('image("%s", width: 100%%)', src)
      or  string.format('image("%s")', src)
    local inner = string.format("rotate(%sdeg, %s)", angle, img)
    local outer = w ~= ""
      and string.format("#box(width: %s, %s)", w, inner)
      or  string.format("#box(%s)", inner)
    return pandoc.RawInline("typst", outer)
  else
    -- HTML: keep as Image inside a Span with rotation style
    local style = string.format("display:inline-block; transform:rotate(%sdeg)", angle)
    return pandoc.Span({el}, pandoc.Attr("", {}, {{"style", style}}))
  end
end

function Span(el)
  for cls, style in pairs(trigger_colors) do
    if el.classes:includes(cls) then
      if FORMAT:match("typst") then
        local open = pandoc.RawInline("typst",
          string.format('#text(weight: "bold", fill: rgb("%s"))[', style.hex))
        local close = pandoc.RawInline("typst", "]")
        local inlines = pandoc.List({open})
        inlines:extend(el.content)
        inlines:insert(close)
        return inlines
      else
        -- HTML: class already on span, CSS handles it
        return el
      end
    end
  end
end

function Div(el)
  for cls, style in pairs(callout_styles) do
    if el.classes:includes(cls) then
      if FORMAT:match("typst") then
        -- Check for custom title attribute
        local label = el.attributes["title"] or style.label

        local open = pandoc.RawBlock("typst", string.format(
          '#block(\n  fill: rgb("%s"),\n  stroke: (left: 4pt + rgb("%s")),\n  inset: (left: 12pt, top: 6pt, bottom: 6pt, right: 8pt),\n  radius: 4pt,\n  width: 100%%,\n)[\n  #text(weight: "bold", size: 0.9em, fill: rgb("%s"))[%s] \\',
          style.bg, style.border, style.text, label
        ))
        local close = pandoc.RawBlock("typst", "]")

        local blocks = pandoc.List({open})
        blocks:extend(el.content)
        blocks:insert(close)
        return blocks
      else
        -- HTML: add a title span as first element, CSS handles the rest
        local label = el.attributes["title"] or style.label
        local title_html = pandoc.RawBlock("html",
          string.format('<p class="callout-title">%s</p>', label))
        el.content:insert(1, title_html)
        return el
      end
    end
  end
end
