"""Runs bin/pkm for the tests. Tests pass their vault with --vault, so they don't depend on where they run, and
they never read the developer's own user config or PKM_VAULT.
"""

import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
PKM = REPO / "bin/pkm"
SHARE_TEMPLATES = REPO / "share/pkm/templates"
NOW = "20261025143012"  # Sunday 2026-10-25, 14:30:12
# The tests run pkm with the bash on PATH; on macOS that is bash 3.2, the oldest one it supports.
BASH = "/bin/bash" if pathlib.Path("/bin/bash").exists() else "bash"


def pkm_env(**extra):
    """This process's environment without PKM_VAULT, plus the variables given (for example PKM_NOW)."""
    environment = {key: value for key, value in os.environ.items() if key != "PKM_VAULT"}
    environment.update(extra)
    return environment


def run_pkm(args, cwd, env, vault=None, stdin=None):
    """Runs pkm with args, from cwd. With vault, passes --vault <vault> before the command."""
    command = [BASH, str(PKM)]
    if vault is not None:
        command += ["--vault", str(vault)]
    if isinstance(stdin, str):
        return subprocess.run([*command, *args], cwd=cwd, env=env, input=stdin, capture_output=True, text=True)
    return subprocess.run([*command, *args], cwd=cwd, env=env, stdin=stdin, capture_output=True, text=True)


class VaultCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._tmp.name)
        self._config = tempfile.TemporaryDirectory()
        self.config_home = self._config.name
        (self.root / ".pkm").mkdir()
        shutil.copytree(SHARE_TEMPLATES, self.root / "templates")

    def tearDown(self):
        self._tmp.cleanup()
        self._config.cleanup()

    def pkm(self, *args, now=NOW, env=None, stdin=None):
        environment = pkm_env(PKM_NOW=now, XDG_CONFIG_HOME=self.config_home, **(env or {}))
        return run_pkm(args, cwd=self.root, env=environment, vault=self.root, stdin=stdin)

    def ok(self, *args, **kwargs):
        result = self.pkm(*args, **kwargs)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def write(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def read(self, rel):
        return (self.root / rel).read_text()

    def exists(self, rel):
        return (self.root / rel).exists()

    def write_user(self, text):
        """Writes the user's pkm config, in the temporary config folder of this test."""
        folder = pathlib.Path(self.config_home) / "pkm"
        folder.mkdir(exist_ok=True)
        (folder / "config").write_text(text)

    @property
    def user_config(self):
        return pathlib.Path(self.config_home) / "pkm/config"
