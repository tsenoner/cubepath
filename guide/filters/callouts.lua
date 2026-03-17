--- Callout box filter for pandoc.
--- Transforms fenced divs (.algorithm, .tip, .caution, .info) into styled
--- blocks for typst output. HTML output uses CSS classes directly.

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

function Div(el)
  for cls, style in pairs(callout_styles) do
    if el.classes:includes(cls) then
      if FORMAT:match("typst") then
        -- Check for custom title attribute
        local label = el.attributes["title"] or style.label

        local open = pandoc.RawBlock("typst", string.format(
          '#block(\n  fill: rgb("%s"),\n  stroke: (left: 4pt + rgb("%s")),\n  inset: (left: 16pt, top: 12pt, bottom: 12pt, right: 12pt),\n  radius: 4pt,\n  width: 100%%,\n)[\n  #text(weight: "bold", size: 0.9em, fill: rgb("%s"))[%s] \\',
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
