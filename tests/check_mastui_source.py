#!/usr/bin/env python3
"""Vérifier le contrat de l'adaptateur contre l'archive officielle, sans compte.

Usage : python3 tests/check_mastui_source.py /chemin/mastui-1.14.2.tar.gz
Ne lance pas Mastui, n'importe pas ses dépendances et n'extrait pas l'archive.
"""
import ast
import hashlib
from pathlib import Path
import sys
import tarfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "payload/lib"))
from common import MASTUI_SHA256, MASTUI_VERSION


def check(path):
    path = Path(path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != MASTUI_SHA256:
        raise ValueError("L'archive n'est pas la distribution 1.14.2 attendue")
    with tarfile.open(path) as archive:
        def source(name):
            return archive.extractfile(f"mastui-{MASTUI_VERSION}/mastui/{name}.py").read().decode()
        app = ast.parse(source("app"))
        klass = next(node for node in app.body if isinstance(node, ast.ClassDef) and node.name == "Mastui")
        methods = {node.name: node for node in klass.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        assert {"on_mount", "select_profile", "load_profile", "show_login_screen"} <= methods.keys()
        assert [a.arg for a in methods["show_login_screen"].args.args] == ["self", "host", "on_cancel"]
        assert "self.register_theme(retro_theme_builtin)" in source("app")
        config = ast.parse(source("config"))
        attrs = {node.attr for node in ast.walk(config) if isinstance(node, ast.Attribute)
                 and isinstance(node.ctx, ast.Store) and isinstance(node.value, ast.Name)
                 and node.value.id == "self"}
        assert {"theme", "preferred_dark_theme", "image_support", "image_renderer",
                "home_auto_refresh_interval", "local_auto_refresh_interval",
                "federated_auto_refresh_interval", "notifications_auto_refresh_interval",
                "federated_timeline_enabled"} <= attrs
        assert 'name="retro-green-builtin"' in source("retro")
        assert 'self.profiles_dir = self.config_dir / "profiles"' in source("profile_manager")
        assert 'id="auth_code"' in source("login")
    print("Mastui 1.14.2 : SHA-256, signatures, thème, configuration, profils et assistant conformes au contrat de l'adaptateur.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    check(sys.argv[1])
