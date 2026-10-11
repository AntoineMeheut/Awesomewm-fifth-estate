"""Adaptation explicite de Mastui 1.14.2, exécutée par son Python pipx.

Utilise ses vrais écrans, API, authentification et profils ; aucun token géré ici.
Les sources de la version sont référencées dans docs/qualification.md.
"""
import importlib.metadata
from copy import deepcopy
import logging
import os
from pathlib import Path
from common import MASTUI_VERSION, load_settings
from diagnostic import memory


def main():
    os.umask(0o077)
    if importlib.metadata.version("mastui") != MASTUI_VERSION:
        raise SystemExit("Version Mastui incompatible. Relancer l'installateur pour rétablir 1.14.2.")
    import mastui.app as upstream
    from mastui.config import Config
    from mastui.profile_manager import profile_manager

    settings = load_settings()
    options = settings["mastodon"]
    colors = settings["theme"]
    # Retain the native theme identity and adapt its grey text/panels to the
    # palette shared with Awesome and xterm. ANSI remapping cannot affect RGB.
    retro_theme = deepcopy(upstream.retro_theme_builtin)
    for field, color in {
        "primary": colors["active"], "secondary": colors["muted"],
        "accent": colors["foreground"], "foreground": colors["foreground"],
        "background": colors["background"], "surface": colors["background"],
        "panel": colors["background"], "warning": colors["warning"],
        "error": colors["warning"], "success": colors["active"],
    }.items():
        setattr(retro_theme, field, color)
    upstream.retro_theme_builtin = retro_theme
    low_memory = 0 < memory().get("MemTotal", 0) < 4 * 1024**3
    # Don't create HTTP/debug logs containing account data in the project logs.
    logging.getLogger().addHandler(logging.NullHandler())

    class RetroConfig(Config):
        def __init__(self, profile_path=None):
            super().__init__(profile_path)
            self.theme = "retro-green-builtin"
            self.preferred_dark_theme = self.theme
            self.image_support = options["media"] == "ansi"
            self.image_renderer = "ansi"
            interval = max(options["refresh_interval"], 120 if low_memory else 10)
            self.home_auto_refresh_interval = interval
            self.local_auto_refresh_interval = interval
            self.federated_auto_refresh_interval = interval
            self.notifications_auto_refresh_interval = interval
            if low_memory:
                self.federated_timeline_enabled = False

    # Version-specific substitution is local to this process, never to installed files.
    upstream.Config = RetroConfig

    class RetroMastui(upstream.Mastui):
        CSS_PATH = str(Path(upstream.__file__).with_name("app.css"))

        def on_mount(self, event):
            # Textual dispatches handlers along the MRO; call the native handler
            # exactly once rather than opening two authentication screens.
            event.prevent_default()
            super().on_mount()
            self.theme = "retro-green-builtin"

        def show_login_screen(self, host=None, on_cancel=None):
            return super().show_login_screen(host=host or options["instance"], on_cancel=on_cancel)

        def select_profile(self):
            preferred = options["profile"]
            if preferred and preferred in profile_manager.get_profiles():
                self.load_profile(preferred)
            else:
                if preferred:
                    self.notify("Profil demandé absent : choisir ou autoriser un compte.")
                super().select_profile()

    app = RetroMastui(ssl_verify=True, debug=False)
    app.run()


if __name__ == "__main__":
    main()
