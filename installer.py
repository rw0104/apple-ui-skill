#!/usr/bin/env python3
"""Install an integrity-checked Apple UI Skill package from its release manifest."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tempfile
from typing import Callable
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import uuid
import zipfile

DEFAULT_MANIFEST = "https://raw.githubusercontent.com/rw0104/apple-ui-skill/main/distribution.json"
PACKAGE_ROOT = "apple-ui-skill"
MANIFEST_LIMIT = 128_000
DOWNLOAD_LIMIT = 64 * 1024 * 1024
EXPANDED_LIMIT = 256 * 1024 * 1024
FILE_LIMIT = 64 * 1024 * 1024
MAX_FILES = 10_000
RECEIPT = ".installation-receipt.json"
VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?\Z")
RESERVED = re.compile(r"(?:CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])(?:\..*)?\Z", re.I)


class InstallError(ValueError):
    pass


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def https_url(value: object) -> str:
    if not isinstance(value, str):
        raise InstallError("A download URL is required.")
    try:
        parsed = urlsplit(value)
        good = (parsed.scheme == "https" and parsed.hostname and not parsed.username
                and not parsed.password and not parsed.fragment and parsed.port in (None, 443))
    except ValueError:
        good = False
    if not good:
        raise InstallError("Downloads require an HTTPS URL without credentials or fragments.")
    return value


class HTTPSRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        https_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download(url: str, limit: int) -> bytes:
    https_url(url)
    request = Request(url, headers={"User-Agent": "apple-ui-skill-installer/1", "Accept": "application/octet-stream"})
    with build_opener(HTTPSRedirects()).open(request, timeout=30) as response:
        https_url(response.geturl())
        length = response.headers.get("Content-Length")
        if length and int(length) > limit:
            raise InstallError("Download exceeds the allowed size.")
        chunks, total = [], 0
        while True:
            chunk = response.read(min(64 * 1024, limit - total + 1))
            if not chunk:
                break
            total += len(chunk)
            if total > limit:
                raise InstallError("Download exceeds the allowed size.")
            chunks.append(chunk)
    return b"".join(chunks)


def json_object(data: bytes, label: str) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise InstallError(f"{label} contains a duplicate key.")
            result[key] = value
        return result
    try:
        value = json.loads(data.decode("utf-8-sig"), object_pairs_hook=pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InstallError(f"{label} is not valid UTF-8 JSON.") from exc
    if not isinstance(value, dict):
        raise InstallError(f"{label} must be an object.")
    return value


def validate_manifest(value: dict) -> dict:
    if type(value.get("schema_version")) is not int or value["schema_version"] != 1:
        raise InstallError("Unsupported distribution manifest schema.")
    if value.get("available") is not True:
        raise InstallError("The publisher has not enabled a downloadable package. Nothing was installed.")
    version = value.get("version")
    sha = value.get("sha256")
    if not isinstance(version, str) or not VERSION.fullmatch(version):
        raise InstallError("Manifest version is missing or invalid.")
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", sha):
        raise InstallError("Manifest requires the package SHA-256.")
    https_url(value.get("package_url"))
    size = value.get("bytes")
    if size is not None and (type(size) is not int or not 0 < size <= DOWNLOAD_LIMIT):
        raise InstallError("Manifest package size is invalid.")
    return value


def package_files(payload: bytes, version: str) -> dict[str, bytes]:
    files, paths, components = {}, {}, {}
    total = 0
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            if len(archive.infolist()) > MAX_FILES:
                raise InstallError("Package contains too many entries.")
            for item in archive.infolist():
                raw = item.orig_filename
                normalized = raw[:-1] if item.is_dir() else raw
                parts = normalized.split("/")
                if (not parts or parts[0] != PACKAGE_ROOT or "\\" in raw or ":" in raw
                        or any(part in ("", ".", "..") or part.endswith((" ", "."))
                               or RESERVED.fullmatch(part) or any(ord(char) < 32 for char in part)
                               for part in parts)
                        or any(part.casefold() == ".git" for part in parts)):
                    raise InstallError(f"Unsafe package path: {raw!r}")
                mode = stat.S_IFMT(item.external_attr >> 16)
                if mode not in (0, stat.S_IFREG, stat.S_IFDIR):
                    raise InstallError(f"Links or special files are not allowed: {raw!r}")
                if len(parts) == 1:
                    if item.is_dir():
                        continue
                    raise InstallError("The package root must be a directory.")
                relative = "/".join(parts[1:])
                key = relative.casefold()
                if key in paths:
                    raise InstallError(f"Duplicate or case-colliding package path: {raw!r}")
                paths[key] = relative
                for count in range(1, len(parts)):
                    component = "/".join(parts[1:count + 1])
                    existing = components.setdefault(component.casefold(), component)
                    if existing != component:
                        raise InstallError(f"Case-colliding directory path: {raw!r}")
                if item.is_dir():
                    continue
                total += item.file_size
                if item.file_size > FILE_LIMIT or total > EXPANDED_LIMIT:
                    raise InstallError("Expanded package exceeds the allowed size.")
                files[relative] = archive.read(item)
    except (zipfile.BadZipFile, NotImplementedError, RuntimeError) as exc:
        raise InstallError("The downloaded package is not a supported, intact ZIP.") from exc
    for name in files:
        for ancestor in PurePosixPath(name).parents:
            key = ancestor.as_posix().casefold()
            if key in paths:
                recorded = paths[key]
                if recorded != ancestor.as_posix() or recorded in files:
                    raise InstallError(f"Conflicting file/directory path: {name!r}")
    if RECEIPT in files:
        raise InstallError("The package must not supply an installation receipt.")
    try:
        skill = files["SKILL.md"].decode("utf-8-sig")
        actual = files["VERSION"].decode("utf-8-sig").strip()
    except (KeyError, UnicodeDecodeError) as exc:
        raise InstallError("Package must include UTF-8 SKILL.md and VERSION.") from exc
    front = skill.split("---", 2)
    if len(front) != 3 or front[0].strip() or not re.search(r"(?m)^name:\s*[\"']?apple-ui-skill[\"']?\s*$", front[1]):
        raise InstallError("The package does not identify the expected apple-ui-skill.")
    if actual != version:
        raise InstallError("Package VERSION does not match the distribution manifest.")
    return files


def redirected(path: Path) -> bool:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400)


def safe_destination(path: Path) -> Path:
    path = Path(os.path.abspath(path.expanduser()))
    if path.parent == path or path.name in ("", ".", ".."):
        raise InstallError("Choose a skill directory, not a filesystem root.")
    for current in (path, *path.parents):
        if redirected(current):
            raise InstallError(f"Installation paths must not contain links or junctions: {current}")
        if current.exists() and not current.is_dir():
            raise InstallError(f"Installation directory is occupied by a file: {current}")
    return path


def default_destination(agent: str, scope: str) -> Path:
    base = Path.home().resolve() if scope == "user" else Path.cwd().resolve()
    directory = {"codex": ".agents", "claude": ".claude", "gemini": ".gemini"}[agent]
    return base / directory / "skills" / PACKAGE_ROOT


@contextmanager
def install_lock(destination: Path):
    path = destination.parent / f".{destination.name}.install.lock"
    if redirected(path):
        raise InstallError("Installer lock must not be a link or junction.")
    handle = path.open("a+b")
    locked = False
    try:
        handle.seek(0, 2)
        if not handle.tell():
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            locked = True
        except OSError as exc:
            raise InstallError("Another installer is using this destination.") from exc
        yield
    finally:
        if locked:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def journal_path(destination: Path) -> Path:
    return destination.parent / f".{destination.name}.install-transaction.json"


def _write_journal(path: Path, value: dict, *, initial: bool = False) -> None:
    data = (json.dumps(value, indent=2) + "\n").encode()
    if initial:
        with path.open("xb") as handle:
            handle.write(data)
        return
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex)
    try:
        temporary.write_bytes(data)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _rename_absent(source: Path, destination: Path) -> None:
    if destination.exists() or redirected(destination):
        raise InstallError(f"A concurrent change occupies the destination: {destination}")
    source.rename(destination)


def recover(destination: Path) -> dict:
    destination = safe_destination(destination)
    if not destination.parent.exists():
        return {"status": "no-recovery-needed", "destination": str(destination)}
    with install_lock(destination):
        journal = journal_path(destination)
        if not journal.exists():
            return {"status": "no-recovery-needed", "destination": str(destination)}
        if redirected(journal):
            raise InstallError("Recovery journal must not be a link or junction.")
        transaction = json_object(journal.read_bytes(), "Recovery journal")
        if transaction.get("destination") != str(destination):
            raise InstallError("Recovery journal belongs to another destination.")
        token = transaction.get("installation_id")
        backup_name = transaction.get("backup")
        if not isinstance(token, str) or not re.fullmatch(r"[0-9a-f]{32}", token):
            raise InstallError("Invalid recovery journal identity.")
        backup = None
        if backup_name is not None:
            if (not isinstance(backup_name, str) or Path(backup_name).name != backup_name
                    or not backup_name.startswith(f".{destination.name}.backup-")
                    or not backup_name.endswith(token)):
                raise InstallError("Invalid recovery backup path.")
            backup = safe_destination(destination.parent / backup_name)
        receipt = destination / RECEIPT
        if destination.exists() and receipt.is_file() and not redirected(receipt):
            installed = json_object(receipt.read_bytes(), "Installation receipt")
            if installed.get("installation_id") == token:
                journal.unlink()
                return {"status": "installation-already-complete", "destination": str(destination),
                        "backup": str(backup) if backup else None}
        if backup and backup.is_dir():
            if destination.exists():
                raise InstallError(f"Recovery found another destination. Preserve both it and {backup}; resolve manually.")
            _rename_absent(backup, destination)
        elif transaction.get("phase") != "prepared":
            raise InstallError("Recovery backup is missing. No user files were changed.")
        journal.unlink()
        return {"status": "recovered", "destination": str(destination)}


def install(manifest: dict, destination: Path, *, update: bool = False,
            downloader: Callable[[str, int], bytes] = download) -> dict:
    manifest = validate_manifest(manifest)
    payload = downloader(manifest["package_url"], DOWNLOAD_LIMIT)
    if len(payload) > DOWNLOAD_LIMIT or (manifest.get("bytes") is not None and len(payload) != manifest["bytes"]):
        raise InstallError("Package byte count does not match the manifest or allowed size.")
    if digest(payload) != manifest["sha256"].lower():
        raise InstallError("Package SHA-256 mismatch. Nothing was installed.")
    files = package_files(payload, manifest["version"])
    destination = safe_destination(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    safe_destination(destination)
    with install_lock(destination):
        journal = journal_path(destination)
        if journal.exists() or redirected(journal):
            raise InstallError("An interrupted installation needs --recover before installing again.")
        if destination.exists():
            if not update:
                raise InstallError("Destination already exists. Use --update to replace it with a preserved backup.")
            if not (destination / "SKILL.md").is_file() or redirected(destination / "SKILL.md"):
                raise InstallError("Refusing to replace a directory that is not an existing skill.")
        token = uuid.uuid4().hex
        backup = destination.parent / f".{destination.name}.backup-{stamp()}-{token}" if destination.exists() else None
        transaction = {"destination": str(destination), "backup": backup.name if backup else None,
                       "installation_id": token, "phase": "prepared"}
        with tempfile.TemporaryDirectory(prefix=f".{destination.name}.staging-", dir=destination.parent) as temporary:
            staged = Path(temporary) / PACKAGE_ROOT
            staged.mkdir()
            for relative, body in files.items():
                path = staged / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(body)
            receipt = {"installation_id": token, "version": manifest["version"],
                       "package_sha256": manifest["sha256"].lower(), "installed_at": stamp()}
            (staged / RECEIPT).write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
            _write_journal(journal, transaction, initial=True)
            moved = False
            try:
                safe_destination(destination)
                if backup:
                    _rename_absent(destination, backup)
                    moved = True
                    transaction["phase"] = "backed-up"
                    _write_journal(journal, transaction)
                _rename_absent(staged, destination)
                transaction["phase"] = "installed"
                _write_journal(journal, transaction)
            except Exception:
                if moved and not destination.exists() and not redirected(destination):
                    _rename_absent(backup, destination)
                    journal.unlink(missing_ok=True)
                elif not moved and not destination.exists():
                    journal.unlink(missing_ok=True)
                raise
            journal.unlink()
        return {"status": "updated" if backup else "installed", "version": manifest["version"],
                "destination": str(destination), "backup": str(backup) if backup else None,
                "package_sha256": manifest["sha256"].lower()}


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="strict")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", choices=("codex", "claude", "gemini"), default="codex")
    parser.add_argument("--scope", choices=("user", "project"), default="user")
    parser.add_argument("--destination", type=Path, help="override the full skill installation directory")
    parser.add_argument("--manifest-url", default=DEFAULT_MANIFEST)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--update", action="store_true", help="replace an existing skill, preserving a timestamped backup")
    action.add_argument("--recover", action="store_true", help="recover an interrupted local installation; no downloads")
    args = parser.parse_args(argv)
    destination = args.destination or default_destination(args.agent, args.scope)
    try:
        if args.recover:
            result = recover(destination)
        else:
            manifest = json_object(download(args.manifest_url, MANIFEST_LIMIT), "Distribution manifest")
            result = install(manifest, destination, update=args.update)
    except (InstallError, OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"Installation stopped: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] in {"installed", "updated"}:
        print("Package installed. Start a new host session to discover the skill. Optional runtime dependencies remain project-specific.")
    return 0


if __name__ == "__main__":
    if sys.version_info < (3, 10):
        raise SystemExit("Python 3.10 or newer is required.")
    raise SystemExit(main())
