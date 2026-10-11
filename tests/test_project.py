import configparser
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "payload/lib"))
import common
import diagnostic
import installer
import runtime


class Workspace(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="retro-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.paths = {"home": self.base / "home", "data": self.base / "data",
                      "config": self.base / "config", "state": self.base / "state"}
        for path in self.paths.values():
            path.mkdir()
        self.defaults = ROOT / "config/settings.ini"
        (self.paths["data"] / "defaults.ini").write_bytes(self.defaults.read_bytes())
        (self.paths["config"] / "settings.ini").write_bytes(self.defaults.read_bytes())
        for module in (common, runtime, installer):
            mock = patch.object(module, "paths", return_value=self.paths)
            mock.start()
            self.addCleanup(mock.stop)

    def change(self, section, key, value):
        parser = configparser.ConfigParser(interpolation=None)
        target = self.paths["config"] / "settings.ini"
        parser.read(target)
        parser[section][key] = value
        with target.open("w") as stream:
            parser.write(stream)


class SettingsTests(Workspace):
    def test_defaults_and_private_runtime(self):
        settings = common.load_settings()
        self.assertEqual(settings["desktop"]["font_size"], 10)
        self.assertFalse(settings["bbs"]["autoconnect"])
        self.assertEqual(settings["irc"]["channels"], [])
        common.write_runtime(settings)
        target = self.paths["config"] / "runtime.lua"
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        self.assertNotIn("mastodon", target.read_text())

    def test_no_tiny_fonts(self):
        self.change("desktop", "font_size", "8")
        with self.assertRaises(ValueError):
            common.load_settings()

    def test_rejects_command_in_host(self):
        self.change("bbs", "host", "xibalba.vip; touch /tmp/UNSAFE")
        with self.assertRaises(ValueError):
            common.load_settings()

    def test_rejects_secrets_in_common_settings(self):
        self.change("mastodon", "token", "do-not-store")
        with self.assertRaises(ValueError):
            common.load_settings()

    def test_rejects_path_as_profile(self):
        for name in ("../outside", "..", "-x;echo hello"):
            self.change("mastodon", "profile", name)
            with self.assertRaises(ValueError):
                common.load_settings()

    def test_https_origin_required(self):
        for origin in ("http://mastodon.social", "https://mastodon.social/auth/sign_in",
                       "https://token@mastodon.social", "https://mastodon.social?token=secret"):
            self.change("mastodon", "instance", origin)
            with self.assertRaises(ValueError):
                common.load_settings()

    def test_lua_paths_are_literal(self):
        value = {'path': '/tmp/a "b" \\ c $(touch x) é'}
        script = self.base / "quote.lua"
        script.write_text("local v=" + common.lua_literal(value) + "\nprint(v.path)\n")
        result = subprocess.run(["lua", str(script)], text=True, capture_output=True, check=True)
        self.assertEqual(result.stdout.rstrip("\n"), value["path"])


class InstallerTests(Workspace):
    def item(self, name="owned", content=b"version 1", preserve=False):
        return {"target": str(self.paths["data"] / name), "content": content,
                "mode": 0o600, "system": False, "preserve": preserve}

    def test_existing_awesome_not_in_package_install(self):
        result = installer.missing_packages({"awesome": "4.3-7"}, common.load_settings())
        self.assertNotIn("awesome", result)
        self.assertIn("ranger", result)

    def test_non_apt_awesome_is_also_reused(self):
        with patch.object(installer.shutil, "which", return_value="/usr/local/bin/awesome"):
            result = installer.missing_packages({}, common.load_settings())
        self.assertNotIn("awesome", result)

    def test_awesome_compatibility_preserves_old_install(self):
        self.assertEqual(installer.check_awesome("awesome v4.3 (Too long)\nother"), "awesome v4.3 (Too long)")
        for version in ("awesome v3.5", "awesome v5.0", "unknown"):
            with self.assertRaises(RuntimeError):
                installer.check_awesome(version)

    def test_plan_does_not_touch_existing_awesome_or_credentials(self):
        plan = installer.build_plan(self.paths, uid=1000)
        targets = [i["target"] for i in plan]
        self.assertFalse(any("/.config/awesome/" in t for t in targets))
        self.assertFalse(any("/mastui/profiles/" in t for t in targets))
        system = [i for i in plan if i["system"]]
        self.assertEqual(len(system), 2)
        launcher = system[0]["content"].decode()
        self.assertIn('"$(id -u)" = "1000"', launcher)

    def test_install_twice_preserves_original_and_mode(self):
        target = self.paths["data"] / "owned"
        target.write_text("original")
        target.chmod(0o640)
        manager = installer.ManagedFiles(self.paths["state"])
        manager.install([self.item()])
        backup = manager.records[str(target)]["original"]
        manager.install([self.item()])
        self.assertEqual(manager.records[str(target)]["original"], backup)
        self.assertEqual(target.read_text(), "version 1")
        manager.uninstall()
        self.assertEqual(target.read_text(), "original")
        self.assertEqual(target.stat().st_mode & 0o777, 0o640)

    def test_reinstall_preserves_personal_settings(self):
        target = self.paths["data"] / "preferences"
        manager = installer.ManagedFiles(self.paths["state"])
        manager.install([self.item("preferences", preserve=True)])
        target.write_text("personal")
        manager.install([self.item("preferences", b"version 2", preserve=True)])
        self.assertEqual(target.read_text(), "personal")
        manager.uninstall()
        self.assertEqual(target.read_text(), "personal")

    def test_update_backs_up_local_changes(self):
        target = self.paths["data"] / "owned"
        manager = installer.ManagedFiles(self.paths["state"])
        manager.install([self.item()])
        target.write_text("local edit")
        manager.install([self.item(content=b"version 2")])
        copies = [f.read_bytes() for f in (self.paths["state"] / "backups").iterdir()]
        self.assertIn(b"local edit", copies)
        manager.uninstall()
        self.assertFalse(target.exists())

    def test_failure_rolls_back_all_files(self):
        manager = installer.ManagedFiles(self.paths["state"])
        first = self.item("first")
        second = self.item("second")
        Path(first["target"]).write_bytes(b"existing")
        original_write = manager.write
        def fail_second(target, *args):
            if Path(target).name == "second":
                raise OSError("simulated disk error")
            original_write(target, *args)
        with patch.object(manager, "write", side_effect=fail_second):
            with self.assertRaises(OSError):
                manager.install([first, second])
        self.assertEqual(Path(first["target"]).read_bytes(), b"existing")
        self.assertFalse(Path(second["target"]).exists())
        self.assertEqual(manager.records, {})
        self.assertFalse(manager.journal_path.exists())

    def test_crash_journal_can_be_recovered(self):
        manager = installer.ManagedFiles(self.paths["state"])
        target = self.paths["data"] / "owned"
        target.write_text("original")
        before = manager.snapshot(target)
        common.json_write(manager.journal_path, {"previous_records": {}, "changes": [
            {"target": str(target), "before": before, "system": False}]})
        target.write_text("half-installed")
        manager.recover()
        self.assertEqual(target.read_text(), "original")
        self.assertFalse(manager.journal_path.exists())

    def test_reinstall_repairs_permissions(self):
        manager = installer.ManagedFiles(self.paths["state"])
        item = self.item()
        manager.install([item])
        Path(item["target"]).chmod(0o666)
        manager.install([item])
        self.assertEqual(Path(item["target"]).stat().st_mode & 0o777, 0o600)

    def test_rejects_symlink_without_changing_target(self):
        external = self.base / "external"
        external.write_text("keep")
        (self.paths["data"] / "owned").symlink_to(external)
        manager = installer.ManagedFiles(self.paths["state"])
        with self.assertRaises(RuntimeError):
            manager.install([self.item()])
        self.assertEqual(external.read_text(), "keep")

    def test_removed_preexisting_file_is_restored(self):
        target = self.paths["data"] / "owned"
        target.write_text("original")
        manager = installer.ManagedFiles(self.paths["state"])
        manager.install([self.item()])
        target.unlink()
        manager.uninstall()
        self.assertEqual(target.read_text(), "original")

    def test_uninstall_works_with_broken_preferences(self):
        self.change("desktop", "font_size", "invalid")
        with patch.object(installer.os, "geteuid", return_value=1000):
            self.assertEqual(installer.main(["uninstall", "--yes"]), 0)


class RuntimeTests(Workspace):
    def test_bbs_has_no_automatic_first_connection(self):
        with patch.object(runtime, "ask", return_value="q"), patch.object(runtime.subprocess, "call") as call:
            self.assertEqual(runtime.bbs(), 0)
            call.assert_not_called()

    def test_bbs_failure_waits_for_manual_retry(self):
        with patch.object(runtime, "ask", side_effect=["", "q"]) as ask, patch.object(runtime.subprocess, "call", return_value=1) as call:
            runtime.bbs()
            self.assertEqual(call.call_count, 1)
            self.assertEqual(ask.call_count, 2)

    def test_bbs_autoconnect_is_only_one_attempt(self):
        self.change("bbs", "autoconnect", "true")
        with patch.object(runtime, "ask", return_value="q"), patch.object(runtime.subprocess, "call", return_value=1) as call:
            runtime.bbs()
            self.assertEqual(call.call_count, 1)

    def test_bbs_encoding_and_palette_are_independent(self):
        self.change("bbs", "encoding", "CP437")
        settings = common.load_settings()
        with patch.object(runtime.shutil, "which", return_value="/usr/bin/luit"):
            self.assertEqual(runtime.bbs_command(settings)[:4], ["luit", "-encoding", "CP437", "--"])
        self.change("bbs", "palette", "standard")
        command = runtime.terminal_command("bbs", common.load_settings())
        self.assertIn("*color1: #cd0000", command)

    def test_telnet_negotiates_on_nonstandard_port(self):
        self.assertEqual(runtime.bbs_command(common.load_settings()),
                         ["telnet", "-8", "--", "xibalba.vip", "-44510"])

    def test_xterm_identity_and_arguments(self):
        for app in common.APPS:
            command = runtime.terminal_command(app, common.load_settings())
            self.assertEqual(command[command.index("-class") + 1], "Retro" + app.capitalize())
            self.assertEqual(command[-2:], ["app", app])
            self.assertIn("*allowWindowOps: false", command)

    def test_launch_lock_prevents_concurrent_duplicate(self):
        entered, finish = threading.Event(), threading.Event()
        def simulated_xterm(command):
            entered.set()
            finish.wait(5)
            return 0
        with patch.object(runtime.subprocess, "call", side_effect=simulated_xterm) as call:
            first = threading.Thread(target=runtime.launch, args=("htop",))
            first.start()
            self.assertTrue(entered.wait(2))
            try:
                self.assertEqual(runtime.launch("htop"), 0)
                self.assertEqual(call.call_count, 1)
            finally:
                finish.set()
                first.join(3)
            self.assertEqual(runtime.launch("htop"), 0)
            self.assertEqual(call.call_count, 2)

    def test_irssi_default_offline_and_native_profile_kept(self):
        runtime.prepare()
        config = self.paths["config"] / "irssi/config"
        config.write_text("native user settings")
        runtime.prepare()
        self.assertEqual(config.read_text(), "native user settings")
        script = (self.paths["config"] / "irssi/scripts/autorun/retro.pl").read_text()
        self.assertNotIn("Irssi::command('connect", script)
        self.assertIn("hors ligne", script)

    def test_irssi_explicit_tls_network(self):
        self.change("irc", "host", "irc.example.org")
        self.change("irc", "channels", "#test #second")
        self.change("irc", "autoconnect", "true")
        script = runtime.irc_script(common.load_settings())
        self.assertIn("-tls -tls_verify -network Retro irc.example.org 6697", script)
        self.assertIn("$server->command('join #test')", script)
        self.assertIn("Irssi::command('connect -tls -tls_verify -network Retro irc.example.org 6697')", script)
        self.assertNotIn("channel add -auto", script)


class DiagnosticTests(unittest.TestCase):
    def test_distribution_gate(self):
        release = {"ID": "linuxmint", "VERSION_ID": "22.3", "UBUNTU_CODENAME": "noble"}
        self.assertTrue(diagnostic.supported(release, "x86_64"))
        self.assertFalse(diagnostic.supported(release, "aarch64"))
        for key, value in (("VERSION_ID", "23"), ("ID", "ubuntu"), ("UBUNTU_CODENAME", "debian")):
            self.assertFalse(diagnostic.supported({**release, key: value}, "x86_64"))

    def test_memory_is_real_and_missing_is_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "meminfo"
            path.write_text("MemTotal: 4096000 kB\nMemAvailable: 1024000 kB\n")
            self.assertEqual(diagnostic.memory(path), {"MemTotal": 4194304000, "MemAvailable": 1048576000})
            self.assertEqual(diagnostic.memory(Path(directory) / "absent"), {})


if __name__ == "__main__":
    unittest.main()
