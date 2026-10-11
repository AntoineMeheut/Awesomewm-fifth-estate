local gears = require("gears")
local awful = require("awful")
require("awful.autofocus")
local wibox = require("wibox")
local beautiful = require("beautiful")
local naughty = require("naughty")
local hotkeys = require("awful.hotkeys_popup")

local config_dir = (os.getenv("XDG_CONFIG_HOME") or os.getenv("HOME") .. "/.config") .. "/retro-awesome"
package.path = config_dir .. "/awesome/?.lua;" .. package.path
local config = dofile(config_dir .. "/runtime.lua")
local geometry = require("geometry")
local widgets = require("widgets")
local theme = config.theme
local launcher = config.paths.data .. "/bin/retro"
local mod = "Mod4"
local order = {"mastui", "bbs", "irssi", "ranger", "htop"}
local dedicated = {irssi = 2, ranger = 3, bbs = 4, mastui = 5, htop = 6}
local classes = { RetroMastui = "mastui", RetroBbs = "bbs", RetroIrssi = "irssi",
                  RetroRanger = "ranger", RetroHtop = "htop" }

beautiful.init({
    font = config.desktop.font .. " " .. config.desktop.font_size,
    bg_normal = theme.background, fg_normal = theme.foreground,
    bg_focus = theme.selection, fg_focus = theme.background,
    bg_urgent = theme.warning, fg_urgent = theme.background,
    border_width = config.desktop.border, border_normal = theme.border,
    border_focus = theme.active, useless_gap = 0,
    taglist_bg_focus = theme.selection, taglist_fg_focus = theme.background,
    tasklist_bg_focus = theme.background, tasklist_fg_focus = theme.active,
    notification_bg = theme.background, notification_fg = theme.foreground,
    notification_border_color = theme.active,
})
naughty.config.defaults.timeout = 6
local handling_error = false
awesome.connect_signal("debug::error", function(err)
    if handling_error then return end
    handling_error = true
    naughty.notify({title = "Erreur Awesome", text = tostring(err), urgency = "critical"})
    handling_error = false
end)

local overview = { name = "retro" }
function overview.arrange(p)
    local boxes = geometry.rectangles(p.workarea, config.desktop, screen[p.screen].dpi or 96)
    for _, c in ipairs(p.clients) do
        local box = boxes[classes[c.class]]
        if box then
            -- Awesome 4.3 subtracts client borders when applying these rectangles.
            p.geometries[c] = { x = box.x, y = box.y,
                width = box.width, height = box.height }
        end
    end
end
awful.layout.layouts = {overview, awful.layout.suit.max, awful.layout.suit.tile}

local function identify(c)
    return classes[c.class]
end

local function assign(c)
    local role = identify(c)
    if role and c.screen and c.screen.tags[6] then
        c:tags({ c.screen.tags[1], c.screen.tags[dedicated[role]] })
        c.floating = false
        c.size_hints_honor = false
    end
end

local function restore_overview(s)
    for _, c in ipairs(s.tags[1]:clients()) do
        c.maximized = false
        c.fullscreen = false
        c.minimized = false
    end
end

local function show(index)
    local s = awful.screen.focused()
    -- Numbered tool shortcuts follow their existing window even on another monitor.
    if index > 1 and index < 7 then
        for _, c in ipairs(client.get()) do
            if dedicated[identify(c)] == index then s = c.screen; break end
        end
    end
    awful.screen.focus(s)
    if index == 1 then restore_overview(s) end
    if s.tags[index] then s.tags[index]:view_only() end
end

local function launch_missing()
    local existing = {}
    for _, c in ipairs(client.get()) do
        local role = identify(c)
        if role then existing[role] = true end
    end
    for _, app in ipairs(order) do
        if not existing[app] then awful.spawn({launcher, "launch", app}, false) end
    end
end

awful.screen.connect_for_each_screen(function(s)
    gears.wallpaper.set(theme.background)
    awful.tag({"1:main", "2:irc", "3:files", "4:bbs", "5:mastui", "6:htop", "7:term"}, s,
        {overview, awful.layout.suit.max, awful.layout.suit.max, awful.layout.suit.max,
         awful.layout.suit.max, awful.layout.suit.max, awful.layout.suit.tile})
    s.tags[1]:connect_signal("property::selected", function(t)
        if t.selected then restore_overview(s) end
    end)
    local tags = awful.widget.taglist({screen = s, filter = awful.widget.taglist.filter.all,
        buttons = gears.table.join(awful.button({}, 1, function(t)
            if t == s.tags[1] then restore_overview(s) end
            t:view_only()
        end))})
    local tasks = awful.widget.tasklist({screen = s, filter = awful.widget.tasklist.filter.focused,
        buttons = gears.table.join(awful.button({}, 1, function(c)
            c:emit_signal("request::activate", "tasklist", {raise = true})
        end))})
    local cpu, ram, status = widgets.new(config)
    s.retro_bar = awful.wibar({position = "top", screen = s,
        height = math.max(config.desktop.bar_height, math.ceil(config.desktop.font_size * (s.dpi or 96) / 72 * 1.5)),
        bg = theme.background, fg = theme.foreground})
    s.retro_bar:setup({layout = wibox.layout.align.horizontal,
        {layout = wibox.layout.fixed.horizontal, tags}, tasks,
        {layout = wibox.layout.fixed.horizontal, cpu, ram, status,
         s == screen.primary and wibox.widget.systray() or wibox.widget.textbox(""),
         wibox.widget.textclock(" %H:%M ")}})
end)

local keys = gears.table.join(
    awful.key({mod}, "Return", function() awful.spawn({launcher, "launch", "terminal"}, false) end,
        {description = "terminal libre", group = "Retro"}),
    awful.key({mod}, "m", function()
        if client.focus then client.focus.maximized = not client.focus.maximized; client.focus:raise() end
    end, {description = "agrandir / restaurer", group = "Retro"}),
    awful.key({mod}, "s", hotkeys.show_help, {description = "aide des raccourcis", group = "Retro"}),
    awful.key({mod}, "l", function() awful.spawn({"xset", "s", "activate"}, false) end,
        {description = "verrouiller", group = "Retro"}),
    awful.key({mod, "Control"}, "r", function()
        awful.spawn.easy_async({launcher, "prepare"}, function(_, stderr, _, code)
            if code == 0 then awesome.restart()
            else naughty.notify({title = "Réglages invalides", text = stderr}) end
        end)
    end, {description = "relire les réglages et recharger", group = "Retro"}),
    awful.key({mod, "Shift"}, "r", launch_missing,
        {description = "rouvrir les outils fermés", group = "Retro"}),
    awful.key({mod, "Shift"}, "q", function()
        awful.menu({items = {{"Quitter Retro Awesome", awesome.quit}, {"Annuler", function() end}}}):show()
    end, {description = "menu de fin de session", group = "Retro"}),
    awful.key({mod}, "j", function() awful.client.focus.byidx(1) end,
        {description = "fenêtre suivante", group = "Retro"}),
    awful.key({mod}, "k", function() awful.client.focus.byidx(-1) end,
        {description = "fenêtre précédente", group = "Retro"}),
    awful.key({}, "XF86AudioRaiseVolume", function()
        awful.spawn({"pactl", "set-sink-volume", "@DEFAULT_SINK@", "+5%"}, false) end),
    awful.key({}, "XF86AudioLowerVolume", function()
        awful.spawn({"pactl", "set-sink-volume", "@DEFAULT_SINK@", "-5%"}, false) end),
    awful.key({}, "XF86AudioMute", function()
        awful.spawn({"pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"}, false) end),
    awful.key({}, "XF86AudioMicMute", function()
        awful.spawn({"pactl", "set-source-mute", "@DEFAULT_SOURCE@", "toggle"}, false) end),
    awful.key({mod}, "p", function() awful.spawn({"xfce4-display-settings"}, false) end,
        {description = "écrans et résolution", group = "Retro"})
)
for i = 1, 7 do
    local index = i
    keys = gears.table.join(keys,
        awful.key({mod}, "#" .. (i + 9), function() show(index) end,
            {description = "vue " .. i, group = "Retro"}),
        awful.key({mod, "Shift"}, "#" .. (i + 9), function()
            local c = client.focus
            if c then c:move_to_tag(c.screen.tags[index]) end
        end, {description = "déplacer vers la vue " .. i, group = "Retro"}))
end
root.keys(keys)

local client_keys = gears.table.join(
    awful.key({mod, "Shift"}, "c", function(c) c:kill() end),
    awful.key({mod, "Control"}, "o", function(c) c:move_to_screen(); assign(c) end))
local client_buttons = gears.table.join(
    awful.button({}, 1, function(c) c:emit_signal("request::activate", "mouse_click", {raise = true}) end),
    awful.button({mod}, 1, function(c)
        c:emit_signal("request::activate", "mouse_click", {raise = true})
        awful.mouse.client.move(c)
    end),
    awful.button({mod}, 3, function(c) awful.mouse.client.resize(c) end))

awful.rules.rules = {
    {rule = {}, properties = {border_width = beautiful.border_width,
        border_color = beautiful.border_normal, focus = awful.client.focus.filter,
        raise = true, keys = client_keys, buttons = client_buttons,
        screen = awful.screen.preferred, placement = awful.placement.no_offscreen},
        callback = function(c)
            if identify(c) then
                if not awesome.startup then c.screen = screen.primary end
                assign(c)
            elseif c.type == "normal" and not c.transient_for then
                c:move_to_tag(c.screen.tags[7])
                if not awesome.startup then c.screen.tags[7]:view_only() end
            end
        end},
    {rule_any = {type = {"dialog", "utility"}}, properties = {floating = true},
        callback = function(c)
            if c.transient_for then c:tags(c.transient_for:tags()) end
            awful.placement.centered(c, {honor_workarea = true})
        end},
}
client.connect_signal("focus", function(c) c.border_color = beautiful.border_focus end)
client.connect_signal("unfocus", function(c) c.border_color = beautiful.border_normal end)
client.connect_signal("mouse::enter", function(c)
    c:emit_signal("request::activate", "mouse_enter", {raise = false})
end)
client.connect_signal("property::screen", function(c) gears.timer.delayed_call(function()
    if c.valid then assign(c) end
end) end)
screen.connect_signal("property::geometry", function(s)
    gears.wallpaper.set(theme.background)
    awful.layout.arrange(s)
end)
screen.connect_signal("removed", function()
    gears.timer.delayed_call(function()
        for _, c in ipairs(client.get()) do assign(c) end
    end)
end)

-- Reuse clients restored by Awesome before attempting any new launch.
gears.timer.start_new(1, function() launch_missing(); return false end)
