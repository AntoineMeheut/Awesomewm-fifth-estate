"""Diagnostic local exportable : aucune lecture des profils applicatifs."""
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess


def probe(argv, timeout=5):
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                                env={**os.environ, "LC_ALL": "C"}, check=False)
        return result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def read(path):
    try:
        return Path(path).read_text().strip()
    except OSError:
        return None


def os_release(path="/etc/os-release"):
    fields = {}
    for line in (read(path) or "").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            fields[key] = value.strip('"')
    return fields


def memory(path="/proc/meminfo"):
    result = {}
    for key, value in re.findall(r"^(MemTotal|MemAvailable):\s+(\d+)",
                                 read(path) or "", re.M):
        result[key] = int(value) * 1024
    return result


def supported(release, arch):
    return (release.get("ID") == "linuxmint" and release.get("VERSION_ID") == "22.3"
            and release.get("UBUNTU_CODENAME") == "noble" and arch == "x86_64")


def collect():
    release = os_release()
    mem = memory()
    display = probe(["xrandr", "--current"]) if os.environ.get("DISPLAY") else None
    # Only connector geometry; no EDID serials, IP addresses, SSIDs or usernames.
    screens = [line for line in (display or "").splitlines()
               if re.match(r"\S+ connected", line)]
    supply = Path("/sys/class/power_supply")
    batteries = [p.name for p in supply.glob("*") if read(p / "type") == "Battery"]
    pci = probe(["lspci", "-k"])
    graphics = []
    keep = False
    for line in (pci or "").splitlines():
        if not line.startswith("\t"):
            keep = bool(re.search(r"VGA|3D controller|Display controller", line))
        if keep:
            graphics.append(line)
    cpu = probe(["lscpu"])
    cpu_lines = [line for line in (cpu or "").splitlines()
                 if re.match(r"(Architecture|CPU\(s\)|Model name):", line)]
    return {
        "system": {k: release.get(k) for k in
                   ("ID", "VERSION_ID", "PRETTY_NAME", "UBUNTU_CODENAME")},
        "architecture": platform.machine(),
        "supported": supported(release, platform.machine()),
        "cpu": cpu_lines or None, "memory_bytes": mem or None,
        "low_memory": bool(mem and mem["MemTotal"] < 4 * 1024**3),
        "disk_free_bytes": {"system": shutil.disk_usage("/").free,
                            "home": shutil.disk_usage(Path.home()).free},
        "displays": screens or None,
        "display_note": None if screens else "Détection différée à la session X11",
        "graphics": graphics or None,
        "network_manager": probe(["systemctl", "is-active", "NetworkManager"]),
        "batteries": batteries,
        "backlight": [p.name for p in Path("/sys/class/backlight").glob("*")],
        "audio_available": probe(["pactl", "info"]) is not None,
        "display_manager": read("/etc/X11/default-display-manager"),
        "session_type": os.environ.get("XDG_SESSION_TYPE"),
        "desktop": os.environ.get("XDG_CURRENT_DESKTOP"),
    }
