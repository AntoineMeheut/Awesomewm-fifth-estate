local geometry = dofile("config/awesome/geometry.lua")
local names = {"mastui", "bbs", "irssi", "ranger", "htop"}
local count = 0
for _, resolution in ipairs({{1024, 768}, {1366, 768}, {1600, 900}, {1920, 1080}, {2560, 1440}}) do
    for _, profile in ipairs({"compact", "wide", "auto"}) do
        for _, font in ipairs({9, 10, 12, 16}) do
            for _, dpi in ipairs({96, 144}) do
                local area = {x = 1366, y = 24, width = resolution[1], height = resolution[2] - 24}
                local options = {layout = profile, font_size = font, gap = 4}
                local boxes = geometry.rectangles(area, options, dpi)
                for i, name in ipairs(names) do
                    local a = assert(boxes[name])
                    assert(a.x >= area.x and a.y >= area.y)
                    assert(a.x + a.width <= area.x + area.width)
                    assert(a.y + a.height <= area.y + area.height)
                    assert(a.width > 0 and a.height > 0)
                    for j = i + 1, #names do
                        local b = boxes[names[j]]
                        assert(a.x + a.width <= b.x or b.x + b.width <= a.x
                               or a.y + a.height <= b.y or b.y + b.height <= a.y,
                               name .. " overlaps " .. names[j])
                    end
                end
                if geometry.profile(area, options, dpi) == "compact" then
                    assert(boxes.mastui.x == boxes.bbs.x)
                    assert(boxes.mastui.y < boxes.bbs.y)
                    assert(boxes.irssi.x == boxes.ranger.x and boxes.ranger.x == boxes.htop.x)
                    assert(boxes.irssi.y < boxes.ranger.y and boxes.ranger.y < boxes.htop.y)
                end
                count = count + 1
            end
        end
    end
end
assert(geometry.profile({width=1366,height=744}, {layout="auto",font_size=10}, 96) == "compact")
assert(geometry.profile({width=2560,height=1416}, {layout="auto",font_size=10}, 96) == "wide")
print("Géométrie : " .. count .. " combinaisons sans recouvrement ni débordement")
