-- Pure geometry, also exercised without an X server by tests/layout_test.lua.
local M = {}

function M.profile(area, options, dpi)
    if options.layout ~= "auto" then return options.layout end
    -- Conservative DejaVu Mono cell estimate; never shrink the font to fit.
    local cell = options.font_size * (dpi or 96) / 72 * 0.64
    local line = options.font_size * (dpi or 96) / 72 * 1.3
    return area.width / cell >= 225 and area.height / line >= 48 and "wide" or "compact"
end

function M.rectangles(area, options, dpi)
    local gap = options.gap
    local x, y = area.x + gap, area.y + gap
    local width, height = area.width - gap * 2, area.height - gap * 2
    local result = {}
    local function rect(key, rx, ry, rw, rh)
        result[key] = { x = rx, y = ry, width = math.max(1, rw), height = math.max(1, rh) }
    end
    if M.profile(area, options, dpi) == "wide" then
        local left = math.floor((width - gap * 2) * 0.40)
        local middle = math.floor((width - gap * 2) * 0.31)
        local right = width - left - middle - gap * 2
        local top = math.floor((height - gap) * 0.56)
        rect("mastui", x, y, left, height)
        rect("bbs", x + left + gap, y, middle, height)
        rect("irssi", x + left + middle + gap * 2, y, right, top)
        local bottom = height - top - gap
        local files = math.floor((bottom - gap) * 0.55)
        rect("ranger", x + left + middle + gap * 2, y + top + gap, right, files)
        rect("htop", x + left + middle + gap * 2, y + top + files + gap * 2,
             right, bottom - files - gap)
    else
        local left = math.floor((width - gap) * 0.58)
        local right = width - left - gap
        local mast = math.floor((height - gap) * 0.62)
        local irc = math.floor((height - gap * 2) * 0.36)
        local files = math.floor((height - gap * 2) * 0.33)
        rect("mastui", x, y, left, mast)
        rect("bbs", x, y + mast + gap, left, height - mast - gap)
        rect("irssi", x + left + gap, y, right, irc)
        rect("ranger", x + left + gap, y + irc + gap, right, files)
        rect("htop", x + left + gap, y + irc + files + gap * 2,
             right, height - irc - files - gap * 2)
    end
    return result
end

return M
