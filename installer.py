#!/usr/bin/env python3
"""Installation utilisateur et gestion réversible des seuls fichiers du projet."""
import argparse
from contextlib import contextmanager
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "payload/lib"))
from common import (MASTUI_SHA256, MASTUI_URL, MASTUI_VERSION, VERSION,
                    atomic_write, json_write, load_settings, lua_literal, paths)
from diagnostic import collect, probe

PACKAGES = ("awesome", "xterm", "htop", "irssi", "ranger", "inetutils-telnet",
            "pipx", "python3-venv", "fonts-dejavu-core", "i3lock", "xss-lock",
            "xfce4-power-manager", "xfce4-settings", "network-manager-gnome",
            "policykit-1-gnome", "pulseaudio-utils", "x11-xserver-utils",
            "x11-utils", "pciutils", "dbus-x11", "scrot")
REQUIRED_COMMANDS = ("awesome", "xterm", "htop", "irssi", "ranger", "telnet", "pipx",
                     "i3lock", "xss-lock", "xfce4-power-manager", "xfsettingsd",
                     "nm-applet", "nmcli", "pactl", "xset", "xrandr", "scrot")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def installed_packages():
    result = probe(["dpkg-query", "-W", "-f=${binary:Package}\t${db:Status-Status}\t${Version}\n"])
    packages = {}
    for line in (result or "").splitlines():
        fields = line.split("\t")
        if len(fields) == 3 and fields[1] == "installed":
            packages[fields[0].split(":")[0]] = fields[2]
    return packages


def missing_packages(installed, settings):
    required = list(PACKAGES)
    if settings["bbs"]["encoding"] == "CP437":
        required.append("luit")
    return [name for name in required if name not in installed
            and not (name == "awesome" and shutil.which("awesome"))]


def check_awesome(version=None):
    version = version or probe(["awesome", "--version"])
    match = re.search(r"awesome v(\d+)\.(\d+)", version or "")
    if not match or (int(match[1]), int(match[2])) < (4, 3) or int(match[1]) != 4:
        raise RuntimeError("Awesome 4.3 ou 4.x plus récent requis ; version actuelle conservée, aucune mise à niveau automatique.")
    return version.splitlines()[0]


def run(argv, env=None):
    result = subprocess.run([str(a) for a in argv], env=env, check=False)
    if result.returncode:
        # No captured app output, environment or secrets in the installation log.
        raise RuntimeError(f"Échec de {Path(str(argv[0])).name} (code {result.returncode})")


def system_targets(uid=None):
    uid = os.getuid() if uid is None else uid
    return (Path(f"/usr/local/bin/retro-awesome-{uid}"),
            Path(f"/usr/share/xsessions/retro-awesome-{uid}.desktop"))


def build_plan(p=None, uid=None):
    p = p or paths()
    uid = os.getuid() if uid is None else uid
    result = []
    def add(target, content, mode=0o600, system=False, preserve=False):
        result.append({"target": str(target), "content": content, "mode": mode,
                       "system": system, "preserve": preserve})
    for source in sorted((ROOT / "payload").rglob("*")):
        if source.is_file() and "__pycache__" not in source.parts and source.suffix != ".pyc":
            relative = source.relative_to(ROOT / "payload")
            add(p["data"] / relative, source.read_bytes(), 0o700 if relative.parts[0] == "bin" else 0o600)
    add(p["data"] / "defaults.ini", (ROOT / "config/settings.ini").read_bytes())
    for source in sorted((ROOT / "config").rglob("*")):
        if source.is_file() and "__pycache__" not in source.parts:
            relative = source.relative_to(ROOT / "config")
            # Native app settings and common preferences belong to the user.
            preserve = relative == Path("settings.ini") or relative.parts[0] in ("htop", "ranger")
            add(p["config"] / relative, source.read_bytes(), preserve=preserve)
    settings = load_settings(p["config"] / "settings.ini", ROOT / "config/settings.ini")
    runtime = {"desktop": settings["desktop"], "theme": settings["theme"],
               "paths": {k: str(v) for k, v in p.items()}}
    add(p["config"] / "runtime.lua", ("return " + lua_literal(runtime) + "\n").encode())
    launcher, desktop = system_targets(uid)
    # No user's executable is ever run by a different account through this entry.
    body = ("#!/bin/sh\nset -eu\n"
            f'[ "$(id -u)" = "{uid}" ] || {{ echo "Session réservée à son utilisateur" >&2; exit 1; }}\n')
    for key, name in (("config", "XDG_CONFIG_HOME"), ("data", "XDG_DATA_HOME"), ("state", "XDG_STATE_HOME")):
        body += "export " + name + "=" + shlex.quote(str(p[key].parent)) + "\n"
    body += "exec " + shlex.quote(str(p["data"] / "bin/session")) + "\n"
    add(launcher, body.encode(), 0o755, system=True)
    entry = ("[Desktop Entry]\nType=Application\n"
             f"Name=Retro Awesome ({uid})\nComment=Bureau terminal vert sur noir\n"
             f"Exec={launcher}\nTryExec={launcher}\nDesktopNames=Awesome;\n"
             "X-LightDM-DesktopName=Retro Awesome\n")
    add(desktop, entry.encode(), 0o644, system=True)
    return result


def validate_stage(plan, require_awesome=True):
    """Check all supplied scripts before activation; no profiles are loaded."""
    if require_awesome:
        check_awesome()
    with tempfile.TemporaryDirectory(prefix="retro-check-") as directory:
        for index, item in enumerate(plan):
            target = Path(item["target"])
            content = item["content"]
            temp = Path(directory) / str(index)
            temp.write_bytes(content)
            if target.suffix == ".lua":
                if require_awesome:
                    run(["awesome", "-k", "-c", temp])
                elif shutil.which("luac"):
                    run(["luac", "-p", temp])
                else:
                    raise RuntimeError("luac requis pour vérifier Lua sur cet hôte")
            if target.suffix == ".py" or content.startswith(b"#!/usr/bin/env python3"):
                compile(content, str(target), "exec")
            if content.startswith(b"#!/bin/sh"):
                run(["sh", "-n", temp])


class ManagedFiles:
    """Write-ahead journal and original-file manifest, including mode bits.

    System destinations are selected by build_plan; all other files are user-owned.
    Application credentials are never registered here.
    """
    def __init__(self, state):
        self.state = Path(state)
        self.manifest_path = self.state / "manifest.json"
        self.journal_path = self.state / "transaction.json"
        self.state.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.records = self.load().get("files", {})

    def load(self):
        return json.loads(self.manifest_path.read_text()) if self.manifest_path.exists() else {}

    def persist(self, status="installed"):
        json_write(self.manifest_path, {"version": VERSION, "uid": os.getuid(),
                                      "status": status, "files": self.records})

    def snapshot(self, target):
        target = Path(target)
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise RuntimeError("Fichier géré non régulier : " + str(target))
        if not target.exists():
            return None
        name = "backups/" + uuid.uuid4().hex
        atomic_write(self.state / name, target.read_bytes())
        return {"file": name, "mode": target.stat().st_mode & 0o777}

    def write(self, target, content, mode, system):
        target = Path(target)
        if system:
            with tempfile.NamedTemporaryFile(prefix="retro-system-") as temporary:
                temporary.write(content)
                temporary.flush()
                # install to a sibling and rename only once the complete file exists.
                staged = str(target) + ".retro-new"
                run(["sudo", "install", "-m", oct(mode)[2:], temporary.name, staged])
                run(["sudo", "mv", "-f", staged, target])
        else:
            atomic_write(target, content, mode)

    def restore(self, target, snapshot, system):
        if snapshot:
            self.write(target, (self.state / snapshot["file"]).read_bytes(), snapshot["mode"], system)
        elif Path(target).exists():
            if system:
                run(["sudo", "rm", "--", target])
            else:
                Path(target).unlink()

    def recover(self):
        if not self.journal_path.exists():
            return
        journal = json.loads(self.journal_path.read_text())
        print("Restauration de la transaction interrompue…")
        for change in reversed(journal["changes"]):
            self.restore(change["target"], change["before"], change["system"])
        self.records = journal["previous_records"]
        self.persist(journal.get("previous_status", "restored"))
        self.journal_path.unlink()

    @contextmanager
    def transaction(self):
        self.recover()
        self.journal = {"previous_records": dict(self.records), "changes": [],
                        "previous_status": self.load().get("status", "restored")}
        json_write(self.journal_path, self.journal)
        try:
            yield
            self.persist()
            self.journal_path.unlink()
        except BaseException:
            self.recover()
            raise

    def before(self, target, system):
        snapshot = self.snapshot(target)
        self.journal["changes"].append({"target": str(target), "before": snapshot, "system": system})
        json_write(self.journal_path, self.journal)
        return snapshot

    def install(self, plan):
        with self.transaction():
            for item in plan:
                target = Path(item["target"])
                key = str(target)
                if item["preserve"]:
                    if not target.exists():
                        self.before(target, False)
                        self.write(target, item["content"], item["mode"], False)
                    continue  # User data remains at uninstall, too.
                prior = self.records.get(key)
                if (target.is_file() and target.read_bytes() == item["content"] and prior
                        and target.stat().st_mode & 0o777 == item["mode"]):
                    continue
                snapshot = self.before(target, item["system"])
                original = prior["original"] if prior else snapshot
                record = {"sha256": sha(item["content"]), "original": original,
                          "system": item["system"], "mode": item["mode"]}
                self.write(target, item["content"], item["mode"], item["system"])
                self.records[key] = record

    def uninstall(self):
        with self.transaction():
            for target, record in list(self.records.items()):
                if Path(target).exists():
                    if sha(Path(target).read_bytes()) != record["sha256"]:
                        print("Modification locale sauvegardée :", target)
                    self.before(target, record["system"])
                else:
                    self.before(target, record["system"])
                self.restore(target, record["original"], record["system"])
                del self.records[target]
        self.persist("removed")


def pipx_env(p):
    return {**os.environ, "PIPX_HOME": str(p["data"] / "pipx"),
            "PIPX_BIN_DIR": str(p["data"] / "pipx-bin"),
            "PIPX_MAN_DIR": str(p["data"] / "pipx-man")}


def mastui_version(p):
    python = p["data"] / "pipx/venvs/mastui/bin/python"
    return probe([str(python), "-c", "import importlib.metadata; print(importlib.metadata.version('mastui'))"])


def install_dependencies(p, settings):
    installed = installed_packages()
    missing = missing_packages(installed, settings)
    if "awesome" in installed or shutil.which("awesome"):
        print("Awesome existant réutilisé :", check_awesome())
    if missing:
        run(["sudo", "apt-get", "update"])
        # Verify candidates on the actual machine, including Mint repository setup.
        for package in missing:
            policy = probe(["apt-cache", "policy", package]) or ""
            if not re.search(r"Candidate:\s+(?!\(none\))\S+", policy):
                raise RuntimeError("Paquet sans candidat dans les dépôts configurés : " + package)
        # No dist-upgrade, no upgrade of installed packages, no replacement WM.
        run(["sudo", "apt-get", "install", "--no-upgrade", "--no-install-recommends", "-y", *missing])
    if mastui_version(p) != MASTUI_VERSION:
        with tempfile.TemporaryDirectory(prefix="retro-mastui-") as directory:
            archive = Path(directory) / f"mastui-{MASTUI_VERSION}.tar.gz"
            with urllib.request.urlopen(MASTUI_URL, timeout=60) as response:
                data = response.read(2 * 1024 * 1024)
            if sha(data) != MASTUI_SHA256:
                raise RuntimeError("Empreinte de la distribution Mastui incorrecte")
            archive.write_bytes(data)
            run(["pipx", "install", "--force", "--python", "/usr/bin/python3", archive], env=pipx_env(p))
    check_dependencies(p, settings)


def check_dependencies(p, settings):
    missing = [command for command in REQUIRED_COMMANDS if not shutil.which(command)]
    if settings["bbs"]["encoding"] == "CP437" and not shutil.which("luit"):
        missing.append("luit")
    if missing:
        raise RuntimeError("Commandes manquantes : " + ", ".join(missing))
    check_awesome()
    if mastui_version(p) != MASTUI_VERSION:
        raise RuntimeError("Mastui 1.14.2 absent de l'environnement pipx dédié")
    # Inspect the installed release's API, without starting an app or reading profiles.
    python = p["data"] / "pipx/venvs/mastui/bin/python"
    run([python, "-c", "import importlib.util; assert importlib.util.find_spec('mastui.app'); "
         "assert importlib.util.find_spec('mastui.config')"])


def describe(plan, settings):
    installed = installed_packages()
    print("Retro Awesome", VERSION)
    print("Cible : Linux Mint 22.3 / Noble, x86_64, session X11")
    print("Awesome déjà installé :", installed.get("awesome") or shutil.which("awesome") or "non détecté")
    print("Paquets à ajouter :", ", ".join(missing_packages(installed, settings)) or "aucun")
    print("Mastui :", MASTUI_VERSION, "dans un environnement pipx propre au projet")
    print("Fichiers gérés :", sum(not i["preserve"] for i in plan))
    print("Réglages et profils personnels : conservés ; ~/.config/awesome n'est pas modifié.")
    print("Fichiers système :", ", ".join(str(p) for p in system_targets()))
    print("APT et pipx ne sont pas annulés par le retrait ; aucun changement de session automatique.")


def verify(p):
    settings = load_settings(defaults=ROOT / "config/settings.ini")
    check_dependencies(p, settings)
    validate_stage(build_plan(p))
    manager = ManagedFiles(p["state"])
    if manager.journal_path.exists():
        raise RuntimeError("Transaction interrompue : lancer install.sh recover")
    if manager.load().get("status") != "installed":
        raise RuntimeError("Aucune installation active dans le manifeste")
    failures = []
    for target, entry in manager.records.items():
        path = Path(target)
        if not path.is_file():
            failures.append("Absent : " + target)
        else:
            if path.suffix == ".lua":
                run(["awesome", "-k", "-c", path])
            if sha(path.read_bytes()) != entry["sha256"]:
                # runtime.lua is intentionally regenerated when preferences change.
                print("Fichier modifié depuis l'installation :", target)
            if path.stat().st_mode & 0o777 != entry["mode"]:
                failures.append("Permissions inattendues : " + target)
    if failures:
        raise RuntimeError("\n".join(failures))
    print("Vérification statique terminée. La recette graphique et matérielle reste distincte.")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Installer la session Retro Awesome sur un Mint existant")
    parser.add_argument("command", choices=("diagnose", "plan", "install", "verify", "uninstall", "recover", "check"))
    parser.add_argument("--yes", action="store_true", help="accepter le plan d'installation ou de retrait")
    parser.add_argument("--json", action="store_true", help="diagnostic JSON sur stdout")
    parser.add_argument("--skip-packages", action="store_true", help="vérifier les dépendances déjà installées sans APT/pipx")
    args = parser.parse_args(argv)
    os.umask(0o077)
    p = paths()
    if args.command == "diagnose":
        print(json.dumps(collect(), indent=2, ensure_ascii=False))
        return 0
    settings = None if args.command in ("uninstall", "recover") else load_settings(defaults=ROOT / "config/settings.ini")
    if args.command == "check":
        validate_stage(build_plan(p), require_awesome=False)
        print("Syntaxes Python, shell, Lua et paramètres : OK")
        return 0
    if args.command == "plan":
        describe(build_plan(p), settings)
        return 0
    if os.geteuid() == 0:
        raise RuntimeError("Exécuter sous votre compte habituel, sans sudo devant install.sh.")
    if args.command == "install":
        diagnosis = collect()
        print(json.dumps(diagnosis, indent=2, ensure_ascii=False))
        if not diagnosis["supported"]:
            raise RuntimeError("Installation limitée à Mint 22.3 / Noble x86_64. Cet hôte n'est pas compatible.")
        if "awesome" in installed_packages() or shutil.which("awesome"):
            check_awesome()
        plan = build_plan(p)
        describe(plan, settings)
        if not args.yes and input("Installer cette session ? [o/N] ").strip().lower() not in ("o", "oui"):
            return 0
    elif args.command == "uninstall":
        print("Retirer les fichiers gérés et restaurer leurs originaux ; conserver paramètres, profils, sauvegardes et paquets.")
        if not args.yes and input("Retirer Retro Awesome ? [o/N] ").strip().lower() not in ("o", "oui"):
            return 0
    p["state"].mkdir(parents=True, exist_ok=True, mode=0o700)
    with (p["state"] / "installer.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Un installateur Retro Awesome travaille déjà.")
        manager = ManagedFiles(p["state"])
        if args.command == "verify":
            verify(p)
        elif args.command == "recover":
            manager.recover()
        elif args.command == "uninstall":
            manager.uninstall()
            print("Session retirée. Vos profils, paquets et sauvegardes sont conservés.")
        elif args.command == "install":
            manager.recover()
            json_write(p["state"] / "diagnostic.json", diagnosis)
            if args.skip_packages:
                check_dependencies(p, settings)
            else:
                install_dependencies(p, settings)
            validate_stage(plan)
            manager.install(plan)
            run([p["data"] / "bin/retro", "prepare"])
            dependency_versions = probe([str(p["data"] / "pipx/venvs/mastui/bin/python"),
                "-c", "import importlib.metadata as m, json; "
                "print(json.dumps({d.metadata['Name']: d.version for d in m.distributions()}))"])
            json_write(p["state"] / "versions.json", {
                "packages": {k: v for k, v in installed_packages().items() if k in PACKAGES},
                "awesome": check_awesome(), "python_dependencies": json.loads(dependency_versions or "{}"),
                "mastui": mastui_version(p), "mastui_sdist_sha256": MASTUI_SHA256})
            verify(p)
            print("Installation terminée. Choisir Retro Awesome à la prochaine connexion.")
            print("L'assistant Mastui s'ouvrira dans son panneau ; Super+5 pour le remplir.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, OSError, EOFError, KeyboardInterrupt) as error:
        # Only controlled operational messages: never persist subprocess streams.
        message = str(error) or "Opération interrompue"
        print("ERREUR : " + message, file=sys.stderr)
        try:
            state = paths()["state"]
            if state.exists():
                atomic_write(state / "last-error.log", dt.datetime.now(dt.timezone.utc).isoformat() +
                             " " + message + "\n")
        except OSError:
            pass
        raise SystemExit(1)
