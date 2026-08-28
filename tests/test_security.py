from __future__ import annotations

import io
import json
import os
import stat
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from betplaycito import __main__ as entrypoint
from betplaycito.server import resolve_storage_paths, verify_password


class StoragePathSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.sandbox = Path(self.temporary.name)
        self.home = self.sandbox / "home"
        self.outside = self.sandbox / "outside"
        self.home.mkdir()
        self.outside.mkdir()
        self.environment = patch.dict(os.environ, {"HOME": str(self.home)}, clear=False)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.trusted_home = patch("betplaycito.server._trusted_user_home", return_value=self.home)
        self.trusted_home.start()
        self.addCleanup(self.trusted_home.stop)
        for name in (
            "BETPLAYCITO_DATA_DIR",
            "BETPLAYCITO_CONFIG",
            "BETPLAYCITO_BACKUP_DIR",
        ):
            os.environ.pop(name, None)

    def test_accepts_private_environment_locations(self) -> None:
        os.environ["BETPLAYCITO_DATA_DIR"] = str(self.home / "data")
        os.environ["BETPLAYCITO_CONFIG"] = str(self.home / "config" / "config.local.json")
        os.environ["BETPLAYCITO_BACKUP_DIR"] = str(self.home / "backups")

        data, config, backups = resolve_storage_paths()

        self.assertEqual(data, self.home / "data")
        self.assertEqual(config, self.home / "config" / "config.local.json")
        self.assertEqual(backups, self.home / "backups")

    def test_rejects_arbitrary_absolute_environment_path(self) -> None:
        os.environ["BETPLAYCITO_DATA_DIR"] = "/etc"

        with self.assertRaisesRegex(RuntimeError, "ubicación de los datos"):
            resolve_storage_paths()

    def test_rejects_blank_environment_path(self) -> None:
        os.environ["BETPLAYCITO_BACKUP_DIR"] = "   "

        with self.assertRaisesRegex(RuntimeError, "ubicación de los respaldos"):
            resolve_storage_paths()

    def test_home_environment_cannot_move_the_trusted_boundary(self) -> None:
        os.environ["HOME"] = "/etc"
        os.environ["BETPLAYCITO_CONFIG"] = "/etc/passwd"

        with self.assertRaisesRegex(RuntimeError, "ubicación de la configuración"):
            resolve_storage_paths()

    def test_filesystem_root_is_never_an_allowed_application_boundary(self) -> None:
        with (
            patch("betplaycito.server.default_project_root", return_value=Path("/")),
            self.assertRaisesRegex(RuntimeError, "ubicación de los datos"),
        ):
            resolve_storage_paths(data_dir=Path("/etc"))

    def test_rejects_sibling_prefix_escape(self) -> None:
        sibling = Path(f"{self.home}-attacker")
        sibling.mkdir()

        with self.assertRaisesRegex(RuntimeError, "ubicación de la configuración"):
            resolve_storage_paths(config_path=sibling / "config.local.json")

    def test_rejects_symlink_escape_before_file_access(self) -> None:
        target = self.outside / "config.local.json"
        target.write_text("{}\n", encoding="utf-8")
        link = self.home / "config.local.json"
        link.symlink_to(target)

        with self.assertRaisesRegex(RuntimeError, "ubicación de la configuración"):
            resolve_storage_paths(config_path=link)


class PasswordConfigurationSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name) / "home"
        self.home.mkdir()
        self.environment = patch.dict(os.environ, {"HOME": str(self.home)}, clear=False)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.trusted_home = patch("betplaycito.server._trusted_user_home", return_value=self.home)
        self.trusted_home.start()
        self.addCleanup(self.trusted_home.stop)
        for name in (
            "BETPLAYCITO_DATA_DIR",
            "BETPLAYCITO_CONFIG",
            "BETPLAYCITO_BACKUP_DIR",
        ):
            os.environ.pop(name, None)

    def test_hash_command_writes_private_config_without_disclosing_secret(self) -> None:
        password = "frase larga y exclusiva de prueba"
        destination = self.home / "config" / "config.local.json"
        destination.parent.mkdir()
        destination.write_text(
            json.dumps(
                {
                    "admin_username": "NelsonSeguro",
                    "admin_password": "texto-que-debe-desaparecer",
                }
            ),
            encoding="utf-8",
        )
        stdout = io.StringIO()
        stderr = io.StringIO()

        with (
            patch("betplaycito.__main__.getpass.getpass", side_effect=[password, password]),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            result = entrypoint._store_password_hash(destination)

        self.assertEqual(result, 0)
        document = json.loads(destination.read_text(encoding="utf-8"))
        encoded = document["admin_password_hash"]
        self.assertEqual(document["admin_username"], "NelsonSeguro")
        self.assertNotIn("admin_password", document)
        self.assertTrue(verify_password(password, encoded))
        combined_output = stdout.getvalue() + stderr.getvalue()
        self.assertNotIn(password, combined_output)
        self.assertNotIn(encoded, combined_output)
        self.assertEqual(list(destination.parent.glob(".*.tmp")), [])
        if os.name != "nt":
            self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o600)

    def test_hash_command_does_not_write_when_confirmation_differs(self) -> None:
        destination = self.home / "config" / "config.local.json"
        stderr = io.StringIO()

        with (
            patch(
                "betplaycito.__main__.getpass.getpass",
                side_effect=["primera contraseña", "segunda contraseña"],
            ),
            redirect_stderr(stderr),
        ):
            result = entrypoint._store_password_hash(destination)

        self.assertEqual(result, 2)
        self.assertFalse(destination.exists())
        self.assertIn("no coinciden", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
