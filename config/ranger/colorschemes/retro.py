from ranger.gui.colorscheme import ColorScheme
from ranger.gui.color import black, green, yellow, default, bold, reverse, normal


class Scheme(ColorScheme):
    progress_bar_color = green

    def use(self, context):
        fg, bg, attr = green, default, normal
        if context.reset:
            return default, default, normal
        if context.selected:
            fg, bg, attr = black, green, bold
        elif context.directory:
            attr = bold
        if context.bad or context.error:
            fg, attr = yellow, bold
        if context.marked:
            attr |= reverse
        return fg, bg, attr
