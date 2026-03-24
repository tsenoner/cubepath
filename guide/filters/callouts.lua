--- Callout box filter for pandoc (Typst output).
--- Transforms fenced divs (.algorithm, .tip, .caution, .info) into styled
--- blocks. Also handles image rotation and algorithm trigger color spans.

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
end

function Span(el)
  for cls, style in pairs(trigger_colors) do
    if el.classes:includes(cls) then
      local open = pandoc.RawInline("typst",
        string.format('#text(weight: "bold", fill: rgb("%s"))[', style.hex))
      local close = pandoc.RawInline("typst", "]")
      local inlines = pandoc.List({open})
      inlines:extend(el.content)
      inlines:insert(close)
      return inlines
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
      -- Convert px to pt for Typst (1px = 0.75pt)
      local num = w:match("^(%d+)px$")
      if num then w = string.format("%.1fpt", tonumber(num) * 0.75) end
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
  -- Detect column widths: 1fr for image columns, auto for text-only
  local col_widths = {}
  if #tbl.bodies > 0 and #tbl.bodies[1].body > 0 then
    local first_row = tbl.bodies[1].body[1]
    for _, cell in ipairs(first_row.cells) do
      local first = cell.contents[1]
      local is_image = #cell.contents == 1
        and (first.t == "Para" or first.t == "Plain")
        and #first.content == 1 and first.content[1].t == "Image"
      table.insert(col_widths, is_image and "1fr" or "auto")
    end
    -- If exactly 1 image with text columns, use auto for image, 1fr for text
    local n_img, n_txt = 0, 0
    for _, w in ipairs(col_widths) do
      if w == "1fr" then n_img = n_img + 1 else n_txt = n_txt + 1 end
    end
    if n_img == 1 and n_txt >= 1 then
      for ci, w in ipairs(col_widths) do
        col_widths[ci] = w == "1fr" and "auto" or "1fr"
      end
    end
    table.insert(parts, string.format("  columns: (%s),", table.concat(col_widths, ", ")))
  else
    table.insert(parts, string.format("  columns: (1fr,) * %d,", ncols))
  end
  table.insert(parts, "  align: center + horizon,")
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
    local open = pandoc.RawBlock("typst", "#align(center)[#set par(justify: false)")
    local close = pandoc.RawBlock("typst", "]")
    local blocks = pandoc.List({open})
    blocks:extend(el.content)
    blocks:insert(close)
    return blocks
  end

  -- Steps list (image + text column layout)
  if el.classes:includes("steps") then
    -- Flatten content: step rows from tables, embedded blocks from processed divs
    local items = {}
    for _, block in ipairs(el.content) do
      if block.t == "Table" then
        for _, body in ipairs(block.bodies) do
          for _, row in ipairs(body.body) do
            table.insert(items, {type = "step", cells = row.cells})
          end
        end
      elseif block.t == "RawBlock" and block.format == "typst" then
        table.insert(items, {type = "embed", text = block.text})
      end
    end
    -- Pass 1: merge each step with its trailing embed (if any)
    local merged = {}
    local j = 1
    while j <= #items do
      if items[j].type == "step" and items[j + 1]
          and items[j + 1].type == "embed" then
        local txt = _cell_to_typst(items[j].cells[2])
        items[j].merged_txt = txt:sub(1, -2) .. "\n" .. items[j + 1].text .. "\n]"
        table.insert(merged, items[j])
        j = j + 2
      else
        table.insert(merged, items[j])
        j = j + 1
      end
    end
    -- Pass 2: pair steps into mirrored grid rows
    local parts = {}
    table.insert(parts, "#grid(")
    table.insert(parts, "  columns: (auto, 1fr, 1fr, auto),")
    table.insert(parts, "  column-gutter: (8pt, 14pt, 8pt),")
    table.insert(parts, "  row-gutter: 4pt,")
    table.insert(parts, "  align: (center + horizon, left + top, left + top, center + horizon),")
    local i = 1
    while i <= #merged do
      local item = merged[i]
      if item.type == "embed" then
        table.insert(parts, string.format(
          "  [], grid.cell(colspan: 2)[\n%s\n], [],", item.text))
        i = i + 1
      else
        local img = _cell_to_typst(item.cells[1])
        local txt = item.merged_txt or _cell_to_typst(item.cells[2])
        local next_item = merged[i + 1]
        if next_item and next_item.type == "step" then
          local img_b = _cell_to_typst(next_item.cells[1])
          local txt_b = next_item.merged_txt or _cell_to_typst(next_item.cells[2])
          table.insert(parts, string.format(
            "  %s, %s, %s, %s,", img, txt, txt_b, img_b))
          i = i + 2
        else
          table.insert(parts, string.format(
            "  %s, grid.cell(colspan: 3)%s,", img, txt))
          i = i + 1
        end
      end
    end
    table.insert(parts, ")")
    return {pandoc.RawBlock("typst", table.concat(parts, "\n"))}
  end

  -- Borderless table wrapper
  if el.classes:includes("borderless") then
    local width = el.attributes["width"]
    local blocks = pandoc.List({})
    for _, block in ipairs(el.content) do
      if block.t == "Table" then
        local grid = _table_to_typst_grid(block)
        if width then
          grid = string.format("#box(width: %s)[\n%s\n]", width, grid)
        end
        blocks:insert(pandoc.RawBlock("typst", grid))
      else
        blocks:insert(block)
      end
    end
    return blocks
  end

  for cls, style in pairs(callout_styles) do
    if el.classes:includes(cls) then
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
    end
  end
end
