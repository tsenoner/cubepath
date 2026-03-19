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

-- Convert a table Cell to a Typst grid item string.
local function _cell_to_typst(cell)
  -- Single image → bare image() call (no content brackets needed)
  local first = cell.contents[1]
  if #cell.contents == 1 and (first.t == "Para" or first.t == "Plain") then
    local para = first
    if #para.content == 1 and para.content[1].t == "Image" then
      local img = para.content[1]
      local w = img.attributes.width or "100%"
      return string.format('image("%s", width: %s)', img.src, w)
    end
  end
  -- Empty cell
  if #cell.contents == 0 then return "[]" end
  -- Text content: render via pandoc and wrap in content brackets
  local typst = pandoc.write(pandoc.Pandoc(cell.contents), "typst")
  typst = typst:gsub("%s+$", "")
  if typst == "" then return "[]" end
  return "[" .. typst .. "]"
end

-- Convert a borderless Table to a Typst #grid() for equal distribution.
local function _table_to_typst_grid(tbl)
  local ncols = #tbl.colspecs
  local parts = {}
  table.insert(parts, "#grid(")
  table.insert(parts, string.format("  columns: (1fr,) * %d,", ncols))
  table.insert(parts, "  align: center,")
  table.insert(parts, "  row-gutter: 2pt,")

  -- Header row: detect group labels (non-empty header cells)
  if #tbl.head.rows > 0 then
    local hcells = tbl.head.rows[1].cells
    local labels = {}
    for _, cell in ipairs(hcells) do
      local text = pandoc.utils.stringify(cell.contents):match("^%s*(.-)%s*$")
      if text ~= "" then
        table.insert(labels, text)
      end
    end
    if #labels > 0 then
      local gsize = math.floor(ncols / #labels)
      local pct = math.floor((gsize - 1) / gsize * 100)
      for _, label in ipairs(labels) do
        table.insert(parts, string.format(
          '  grid.cell(colspan: %d, align: center)[%s\\ #line(length: %d%%, stroke: 0.5pt + luma(180))],',
          gsize, label, pct))
      end
    end
  end

  -- Body rows
  for _, body in ipairs(tbl.bodies) do
    for _, row in ipairs(body.body) do
      local items = {}
      for _, cell in ipairs(row.cells) do
        table.insert(items, _cell_to_typst(cell))
      end
      table.insert(parts, "  " .. table.concat(items, ", ") .. ",")
    end
  end

  table.insert(parts, ")")
  return table.concat(parts, "\n")
end

function Div(el)
  -- Centered block (no justification, center-aligned)
  if el.classes:includes("center") then
    if FORMAT:match("typst") then
      local open = pandoc.RawBlock("typst", "#align(center)[#set par(justify: false)")
      local close = pandoc.RawBlock("typst", "]")
      local blocks = pandoc.List({open})
      blocks:extend(el.content)
      blocks:insert(close)
      return blocks
    else
      el.attributes["style"] = "text-align: center;"
      return el
    end
  end

  -- Borderless table wrapper
  if el.classes:includes("borderless") then
    if FORMAT:match("typst") then
      local blocks = pandoc.List({})
      for _, block in ipairs(el.content) do
        if block.t == "Table" then
          blocks:insert(pandoc.RawBlock("typst", _table_to_typst_grid(block)))
        else
          blocks:insert(block)
        end
      end
      return blocks
    else
      return el  -- HTML: class on div, CSS handles it
    end
  end

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
