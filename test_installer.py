"""Focused temporary-fixture tests for public installation and update behavior."""

from __future__ import annotations

import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import uuid
import zipfile

import installer


def payload(version="1.0.0", additions=()):
    rows = [("apple-ui-skill/SKILL.md", b"---\nname: apple-ui-skill\ndescription: Fixture only.\n---\nFixture\n"),
            ("apple-ui-skill/VERSION", version.encode()),
            ("apple-ui-skill/scripts/run.py", b"print('fixture')\n"), *additions]
    with io.BytesIO() as buffer:
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, body in rows:
                item = zipfile.ZipInfo("placeholder")
                item.filename = name
                archive.writestr(item, body)
        return buffer.getvalue()


def release(data, version="1.0.0"):
    return {"schema_version": 1, "available": True, "version": version,
            "package_url": "https://example.invalid/fixture.zip", "sha256": installer.digest(data), "bytes": len(data)}


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="skill installer test ")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.destination = self.root / "skills/apple-ui-skill"
        self.data = payload()
        self.manifest = release(self.data)

    def install(self, data=None, manifest=None, **kwargs):
        return installer.install(manifest or self.manifest, self.destination,
                                 downloader=lambda url, limit: data or self.data, **kwargs)

    def test_installs_verified_package_and_receipt(self):
        result = self.install()
        self.assertEqual("installed", result["status"])
        self.assertEqual(b"1.0.0", (self.destination / "VERSION").read_bytes())
        receipt = json.loads((self.destination / installer.RECEIPT).read_text())
        self.assertEqual(self.manifest["sha256"], receipt["package_sha256"])
        self.assertFalse(installer.journal_path(self.destination).exists())
        self.assertFalse(list(self.destination.parent.glob("*.staging-*")))

    def test_existing_skill_requires_update_and_backup_keeps_local_files(self):
        self.install()
        (self.destination / "my-notes.txt").write_text("User edits survive in backup.")
        with self.assertRaisesRegex(installer.InstallError, "--update"):
            self.install()
        next_package = payload("1.0.1")
        result = self.install(next_package, release(next_package, "1.0.1"), update=True)
        backup = Path(result["backup"])
        self.assertEqual("updated", result["status"])
        self.assertEqual("1.0.1", (self.destination / "VERSION").read_text())
        self.assertEqual("1.0.0", (backup / "VERSION").read_text())
        self.assertEqual("User edits survive in backup.", (backup / "my-notes.txt").read_text())

    def test_hash_version_and_unavailable_fail_before_writing(self):
        for changes, message in (({"sha256": "0" * 64}, "SHA-256"),
                                 ({"version": "1.2.3"}, "VERSION"),
                                 ({"available": False}, "not enabled"),
                                 ({"package_url": "http://example.invalid/file"}, "HTTPS")):
            with self.subTest(changes=changes):
                with self.assertRaisesRegex(installer.InstallError, message):
                    self.install(manifest={**self.manifest, **changes})
                self.assertFalse(self.destination.parent.exists())

    def test_paths_reject_traversal_reserved_and_case_collisions(self):
        bad_entries = (
            [("apple-ui-skill/../outside.txt", b"x")],
            [("other-root/a.txt", b"x")],
            [("apple-ui-skill/references/NUL.txt", b"x")],
            [("apple-ui-skill/references/bad. ", b"x")],
            [("apple-ui-skill/references\\wrong.txt", b"x")],
            [("apple-ui-skill/.git/config", b"x")],
            [("apple-ui-skill/a/foo.md", b"x"), ("apple-ui-skill/A/bar.md", b"y")],
            [("apple-ui-skill/scripts/RUN.py", b"x")],
            [("apple-ui-skill/file", b"x"), ("apple-ui-skill/file/nested", b"y")],
        )
        for entries in bad_entries:
            with self.subTest(entries=entries), self.assertRaises(installer.InstallError):
                installer.package_files(payload(additions=entries), "1.0.0")

    def test_archive_links_are_rejected(self):
        with io.BytesIO(self.data) as buffer:
            with zipfile.ZipFile(buffer, "a") as archive:
                item = zipfile.ZipInfo("apple-ui-skill/link.md")
                item.create_system = 3
                item.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(item, "outside")
            linked = buffer.getvalue()
        with self.assertRaisesRegex(installer.InstallError, "Links"):
            installer.package_files(linked, "1.0.0")

    def test_failed_promotion_restores_old_directory(self):
        self.install()
        original = installer._rename_absent

        def fail_promotion(source, destination):
            if ".staging-" in source.parent.name:
                raise OSError("simulated promotion failure")
            original(source, destination)

        with patch.object(installer, "_rename_absent", side_effect=fail_promotion):
            with self.assertRaisesRegex(OSError, "simulated"):
                self.install(update=True)
        self.assertTrue((self.destination / "SKILL.md").is_file())
        self.assertEqual("1.0.0", (self.destination / "VERSION").read_text())
        self.assertFalse(installer.journal_path(self.destination).exists())

    def test_recovery_restores_interrupted_backup_and_preserves_conflicts(self):
        self.install()
        token = uuid.uuid4().hex
        backup = self.destination.parent / f".{self.destination.name}.backup-test-{token}"
        self.destination.rename(backup)
        journal = installer.journal_path(self.destination)
        journal.write_text(json.dumps({"destination": str(self.destination), "backup": backup.name,
                                       "installation_id": token, "phase": "backed-up"}))
        self.destination.mkdir()
        (self.destination / "concurrent.txt").write_text("Keep this edit.")
        with self.assertRaisesRegex(installer.InstallError, "another destination"):
            installer.recover(self.destination)
        self.assertTrue(backup.exists())
        self.assertTrue(journal.exists())
        (self.destination / "concurrent.txt").unlink()
        self.destination.rmdir()
        result = installer.recover(self.destination)
        self.assertEqual("recovered", result["status"])
        self.assertEqual("1.0.0", (self.destination / "VERSION").read_text())

    def test_two_installers_cannot_share_destination_lock(self):
        self.destination.parent.mkdir()
        with installer.install_lock(self.destination):
            with self.assertRaisesRegex(installer.InstallError, "Another installer"):
                self.install()

    def test_host_paths_and_scope_are_explicit(self):
        with patch.object(Path, "home", return_value=self.root):
            self.assertEqual(self.root / ".agents/skills/apple-ui-skill", installer.default_destination("codex", "user"))
            self.assertEqual(self.root / ".claude/skills/apple-ui-skill", installer.default_destination("claude", "user"))
        with patch.object(Path, "cwd", return_value=self.root):
            self.assertEqual(self.root / ".gemini/skills/apple-ui-skill", installer.default_destination("gemini", "project"))


if __name__ == "__main__":
    unittest.main()
