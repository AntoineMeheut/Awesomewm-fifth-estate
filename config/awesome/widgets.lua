local awful = require("awful")
local gears = require("gears")
local wibox = require("wibox")
local M = {}

local function file(path)
    local f = io.open(path, "r")
    if not f then return nil end
    local data = f:read("*a")
    f:close()
    return data
end

function M.new(config)
    local cpu = wibox.widget.textbox(" CPU — ")
    local ram = wibox.widget.textbox(" RAM — ")
    local status = wibox.widget.textbox(" NET ? ")
    local last_total, last_idle
    local function update()
        local stat = file("/proc/stat") or ""
        local numbers = stat:match("^cpu%s+([^\n]+)")
        if numbers then
            local fields = {}
            for n in numbers:gmatch("%d+") do fields[#fields + 1] = tonumber(n) end
            local total = 0
            -- guest and guest_nice are already included in user/nice.
            for i = 1, math.min(8, #fields) do total = total + fields[i] end
            local idle = (fields[4] or 0) + (fields[5] or 0)
            if last_total and total > last_total then
                local used = 100 * (1 - (idle - last_idle) / (total - last_total))
                cpu.text = string.format(" CPU %02d%% ", math.floor(math.max(0, math.min(100, used))))
            end
            last_total, last_idle = total, idle
        end
        local mem = file("/proc/meminfo") or ""
        local total = tonumber(mem:match("MemTotal:%s+(%d+)"))
        local available = tonumber(mem:match("MemAvailable:%s+(%d+)"))
        if total and available and total > 0 then
            ram.text = string.format(" RAM %02d%% ", math.floor(100 * (1 - available / total)))
        end
    end
    gears.timer { timeout = config.desktop.cpu_interval, autostart = true,
                  call_now = true, callback = update }
    awful.widget.watch({config.paths.data .. "/bin/retro", "status"},
        config.desktop.status_interval, function(widget, stdout)
            widget.text = " " .. stdout:gsub("%s+$", "") .. " "
        end, status)
    status:buttons(gears.table.join(awful.button({}, 1, function()
        awful.spawn({"nm-connection-editor"}, false)
    end)))
    return cpu, ram, status
end

return M
