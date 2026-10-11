"""Lanceurs des applications réelles, sans shell pour les paramètres utilisateur."""
import argparse
import fcntl
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys

from common import APPS, atomic_write, load_settings, paths, write_runtime
from diagnostic import memory, probe, read


def palette(settings, standard=False):
    t = settings["theme"]
    if standard:
        return ["#000000", "#cd0000", "#00cd00", "#cdcd00", "#5c5cff", "#cd00cd",
                "#00cdcd", "#e5e5e5", "#7f7f7f", "#ff5555", "#55ff55", "#ffff55",
                "#8888ff", "#ff55ff", "#55ffff", "#ffffff"]
    return [t["background"], t["warning"], t["foreground"], "#98ce7c", t["muted"],
            "#72bd88", "#60d29a", t["foreground"], t["muted"], "#ffe292",
            t["active"], "#c2eda2", "#77bd8c", "#a6dcb3", "#adf7cf", "#d5ffe0"]


def terminal_command(app, settings):
    p = paths()
    d, t = settings["desktop"], settings["theme"]
    command = ["xterm", "-class", "Retro" + app.capitalize(), "-name", "retro-" + app,
               "-title", app.upper(), "-fa", d["font"], "-fs", str(d["font_size"]),
               "-bg", t["background"], "-fg", t["foreground"], "-cr", t["active"],
               "-bc", "+sb", "-b", "4", "-u8", "-xrm", "*visualBell: true",
               "-xrm", "*allowWindowOps: false", "-xrm", "*allowTitleOps: false",
               "-xrm", "*cursorBlink: false", "-xrm", "*saveLines: 2000",
               "-xrm", "*termName: xterm-256color", "-xrm", "*colorBDMode: false",
               "-xrm", "*colorULMode: false",
               "-xrm", "*highlightColor: " + t["selection"],
               "-xrm", "*highlightTextColor: " + t["background"]]
    for i, color in enumerate(palette(settings, app == "bbs" and settings["bbs"]["palette"] == "standard")):
        command += ["-xrm", f"*color{i}: {color}"]
    # xterm -e must be last: all following values are literal child arguments.
    return command + ["-e", str(p["data"] / "bin/retro"), "app", app]


def launch(app):
    p = paths()
    settings = load_settings()
    if app == "terminal":
        return subprocess.call(terminal_command(app, settings))
    run = p["state"] / "run"
    run.mkdir(parents=True, exist_ok=True, mode=0o700)
    display = hashlib.sha256(os.environ.get("DISPLAY", "none").encode()).hexdigest()[:12]
    # The parent keeps the lock while xterm lives, including during Awesome restarts.
    with (run / f"{display}-{app}.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        return subprocess.call(terminal_command(app, settings))


def ask(prompt):
    try:
        return input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return "q"


def bbs_command(settings):
    b = settings["bbs"]
    # GNU Telnet suppresses initial negotiation on nonstandard ports unless the
    # port has a '-' prefix. '--' keeps that prefix out of option parsing.
    command = ["telnet", "-8", "--", b["host"], "-" + str(b["port"])]
    if b["encoding"] == "CP437":
        if not shutil.which("luit"):
            raise ValueError("CP437 nécessite luit ; repasser à UTF-8 ou installer luit.")
        command = ["luit", "-encoding", "CP437", "--"] + command
    return command


def bbs():
    settings = load_settings()
    b = settings["bbs"]
    print(f"BBS TELNET — {b['host']}:{b['port']} — {b['encoding']}\n")
    connect = b["autoconnect"]
    while True:
        if not connect and ask("[Entrée] Se connecter / réessayer · [q] Fermer : ") == "q":
            return 0
        connect = False  # No silent retry and no replay of credentials.
        try:
            status = subprocess.call(bbs_command(load_settings()))
            print(f"\nConnexion terminée (code {status}).")
        except (OSError, ValueError) as error:
            print("\nConnexion impossible :", error)
        except KeyboardInterrupt:
            print("\nConnexion interrompue.")


def irc_script(settings):
    i = settings["irc"]
    # All interpolated tokens were restricted by the settings schema.
    commands = ["set theme retro", "set nick " + i["nick"], "set term_charset UTF-8"]
    connect_command = None
    if i["host"]:
        commands += ["network add " + i["network"]]
        tls = "-tls -tls_verify " if i["tls"] else "-notls "
        endpoint = f"{tls}-network {i['network']} {i['host']} {i['port']}"
        commands += ["server add -noauto " + endpoint]
        if i["autoconnect"]:
            connect_command = "connect " + endpoint
    result = "use strict;\nuse warnings;\nuse Irssi;\n"
    result += "\n".join("Irssi::command('" + c + "');" for c in commands) + "\n"
    if i["host"] and i["channels"]:
        # Explicit joins at connection time don't leave stale -auto entries in
        # the native config after the user removes a channel from settings.ini.
        result += ("Irssi::signal_add('server connected', sub {\n"
                   "  my ($server) = @_;\n"
                   "  return unless ($server->{chatnet} // '') eq '" + i["network"] + "';\n"
                   "  return unless ($server->{address} // '') eq '" + i["host"] + "';\n")
        for channel in i["channels"]:
            result += "  $server->command('join " + channel + "');\n"
        result += "});\n"
    if connect_command:
        result += "Irssi::command('" + connect_command + "');\n"
    if not i["autoconnect"]:
        help_text = ("Retro : hors ligne. /nick pseudo ; /connect -tls serveur 6697 ; "
                     "/join #salon. /help connect pour les options. "
                     "Configurer settings.ini pour la connexion automatique.")
        result += "Irssi::print('" + help_text + "');\n"
    return result


def prepare():
    settings = load_settings()
    p = paths()
    # Existing profiles and their credentials never enter the installer manifest.
    irssi = p["config"] / "irssi"
    irssi.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not (irssi / "config").exists():
        atomic_write(irssi / "config", 'servers = ();\nchatnets = {};\nchannels = ();\nsettings = { core = { real_name = "Retro Awesome"; }; };\n')
    atomic_write(irssi / "scripts/autorun/retro.pl", irc_script(settings))
    write_runtime(settings)
    return 0


def run_app(app):
    p = paths()
    if app == "bbs":
        return bbs()
    if app == "terminal":
        os.execv(os.environ.get("SHELL", "/bin/sh"), [os.environ.get("SHELL", "/bin/sh")])
    settings = load_settings()
    commands = {
        "htop": ["htop"],
        "ranger": ["ranger", "--confdir=" + str(p["config"] / "ranger"), str(p["home"])],
        "irssi": ["irssi", "--home=" + str(p["config"] / "irssi"), "--noconnect"],
        "mastui": [str(p["data"] / "pipx/venvs/mastui/bin/python"),
                   str(p["data"] / "lib/mastui_adapter.py")],
    }
    env = {**os.environ, "HTOPRC": str(p["config"] / "htop/htoprc")}
    if app == "irssi":
        prepare()
    if app == "mastui" and not settings["mastodon"]["autoconnect"]:
        if ask("MASTUI — [Entrée] Ouvrir le client · [q] Fermer : ") == "q":
            return 0
    while True:
        try:
            code = subprocess.call(commands[app], env=env)
            print(f"\n{app.upper()} terminé (code {code}).")
        except OSError:
            print(f"\nImpossible de démarrer {app}. Exécuter install.sh verify.")
        except KeyboardInterrupt:
            print("\nApplication interrompue.")
        if ask("[Entrée] Relancer · [q] Fermer ce panneau : ") == "q":
            return 0


def status():
    network = probe(["nmcli", "-t", "-f", "STATE", "general"])
    label = "NET ?" if network is None else ("NET connecté" if network.split(":")[0] in
                                             ("connected", "connected (site only)", "connected (local only)") else "NET hors ligne")
    batteries = []
    for battery in Path("/sys/class/power_supply").glob("*"):
        if read(battery / "type") == "Battery":
            capacity = read(battery / "capacity")
            state = read(battery / "status")
            if capacity and capacity.isdigit():
                batteries.append(capacity + "%" + ("+" if state == "Charging" else ""))
    print(label + " | " + ("BAT " + "/".join(batteries) if batteries else "SECTEUR"))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Outils de la session Retro Awesome")
    sub = parser.add_subparsers(dest="action", required=True)
    for command in ("launch", "app"):
        sub.add_parser(command).add_argument("tool", choices=(*APPS, "terminal"))
    for command in ("prepare", "status"):
        sub.add_parser(command)
    args = parser.parse_args(argv)
    os.umask(0o077)
    try:
        if args.action == "launch":
            return launch(args.tool)
        if args.action == "app":
            return run_app(args.tool)
        return prepare() if args.action == "prepare" else status()
    except (OSError, ValueError) as error:
        print("Retro Awesome :", error, file=sys.stderr)
        return 1
