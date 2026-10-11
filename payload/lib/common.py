"""Configuration partagée ; bibliothèque standard uniquement."""
import configparser
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlparse

VERSION = "0.1.0"
MASTUI_VERSION = "1.14.2"
MASTUI_URL = ("https://files.pythonhosted.org/packages/03/f3/"
              "972f0b99fb2766227792cf24ff30d6626b8db96bd2c463fe25e743a20f69/"
              "mastui-1.14.2.tar.gz")
MASTUI_SHA256 = "1df50fb41bbfa5c8f07028aa94b5f2881b4732b2d6a62d5846f110fdeb38a8d1"
APPS = ("mastui", "bbs", "irssi", "ranger", "htop")


def paths():
    home = Path.home()
    def xdg(key, default):
        value = Path(os.environ.get(key, str(home / default)))
        if not value.is_absolute():
            raise ValueError(key + " doit être un chemin absolu")
        return value / "retro-awesome"
    return {"home": home, "config": xdg("XDG_CONFIG_HOME", ".config"),
            "data": xdg("XDG_DATA_HOME", ".local/share"),
            "state": xdg("XDG_STATE_HOME", ".local/state")}


def atomic_write(path, content, mode=0o600):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink():
        raise ValueError("Lien symbolique refusé : " + str(path))
    fd, temporary = tempfile.mkstemp(prefix=".retro-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content.encode() if isinstance(content, str) else content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_settings(path=None, defaults=None):
    p = paths()
    parser = configparser.ConfigParser(interpolation=None)
    defaults = defaults or p["data"] / "defaults.ini"
    parser.read(defaults, encoding="utf-8")
    selected = Path(path or p["config"] / "settings.ini")
    parser.read(selected, encoding="utf-8")
    if not parser.has_section("desktop"):
        raise ValueError("Configuration absente : " + str(selected))
    out = {section: dict(parser[section]) for section in parser.sections()}
    expected = {"desktop", "theme", "bbs", "irc", "mastodon"}
    if set(out) != expected:
        raise ValueError("Sections de configuration invalides")
    # A strict schema catches misspellings and prevents accidental secret storage.
    schema = {
        "desktop": "font font_size layout gap border bar_height cpu_interval status_interval",
        "theme": "background foreground muted border active selection warning",
        "bbs": "host port encoding palette autoconnect",
        "irc": "host port network nick channels tls autoconnect",
        "mastodon": "instance profile autoconnect media refresh_interval",
    }
    for section, keys in schema.items():
        if set(out[section]) != set(keys.split()):
            raise ValueError("Clés invalides dans [" + section + "]")
        for value in out[section].values():
            if any(ord(c) < 32 for c in value):
                raise ValueError("Caractère de contrôle interdit")
    for section, key, lo, hi in [
        ("desktop", "font_size", 9, 28), ("desktop", "gap", 0, 32),
        ("desktop", "border", 0, 8), ("desktop", "bar_height", 18, 64),
        ("desktop", "cpu_interval", 1, 60), ("desktop", "status_interval", 5, 300),
        ("bbs", "port", 1, 65535), ("irc", "port", 1, 65535),
        ("mastodon", "refresh_interval", 10, 3600),
    ]:
        n = int(out[section][key])
        if not lo <= n <= hi:
            raise ValueError(f"{section}.{key} doit être compris entre {lo} et {hi}")
        out[section][key] = n
    for section, key in [("bbs", "autoconnect"), ("irc", "autoconnect"),
                         ("irc", "tls"), ("mastodon", "autoconnect")]:
        out[section][key] = parser.getboolean(section, key)
    for section, key, choices in [
        ("desktop", "layout", {"auto", "compact", "wide"}),
        ("bbs", "encoding", {"UTF-8", "CP437"}),
        ("bbs", "palette", {"green", "standard"}),
        ("mastodon", "media", {"off", "ansi"}),
    ]:
        if out[section][key] not in choices:
            raise ValueError(f"Valeur inconnue pour {section}.{key}")
    for value in out["theme"].values():
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
            raise ValueError("Couleur attendue au format #RRGGBB")
    host_re = r"[A-Za-z0-9][A-Za-z0-9.:-]{0,252}"
    for section in ("bbs", "irc"):
        host = out[section]["host"]
        if not re.fullmatch(host_re, host) and (host or section == "bbs"):
            raise ValueError("Hôte invalide dans " + section)
    for key in ("nick", "network"):
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_\-]{0,39}", out["irc"][key]):
            raise ValueError("irc." + key + " invalide")
    channels = out["irc"]["channels"].split()
    if any(not re.fullmatch(r"#[A-Za-z0-9_+.#\-]{1,80}", c) for c in channels):
        raise ValueError("Salons IRC invalides : séparer les #salons par des espaces")
    out["irc"]["channels"] = channels
    url = urlparse(out["mastodon"]["instance"])
    if (url.scheme != "https" or not url.hostname or url.username or url.password
            or url.path not in ("", "/") or url.query or url.fragment):
        raise ValueError("L'instance Mastodon doit être une origine HTTPS")
    profile = out["mastodon"]["profile"]
    if profile and not re.fullmatch(r"[A-Za-z0-9_@.\-]{1,150}", profile):
        raise ValueError("Nom de profil Mastui invalide")
    if profile in (".", ".."):
        raise ValueError("Nom de profil Mastui invalide")
    if not re.fullmatch(r"[A-Za-z0-9 _-]{1,80}", out["desktop"]["font"]):
        raise ValueError("Nom de police invalide")
    return out


def lua_literal(value):
    if isinstance(value, dict):
        return "{" + ",".join("[" + lua_literal(k) + "]=" + lua_literal(v)
                              for k, v in value.items()) + "}"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    # UTF-8 literals, with explicit Lua-compatible escaping.
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r") + '"'


def write_runtime(settings):
    p = paths()
    values = {"desktop": settings["desktop"], "theme": settings["theme"],
              "paths": {k: str(v) for k, v in p.items()}}
    atomic_write(p["config"] / "runtime.lua", "return " + lua_literal(values) + "\n")


def json_write(path, obj):
    atomic_write(path, json.dumps(obj, indent=2, ensure_ascii=False) + "\n")
