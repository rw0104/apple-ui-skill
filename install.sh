#!/bin/sh
# Requires Python 3.10+. All options are forwarded to installer.py.
set -eu

installer_python=''
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 &&
       "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
        installer_python="$candidate"
        break
    fi
done
if [ -z "$installer_python" ]; then
    printf '%s\n' 'Install Python 3.10 or newer, then run this installer again.' >&2
    exit 1
fi

installer_temp="$(mktemp "${TMPDIR:-/tmp}/apple-ui-install.XXXXXXXX")"
trap 'rm -f -- "$installer_temp"' EXIT HUP INT TERM
"$installer_python" - "$installer_temp" <<'PY'
from pathlib import Path
import sys
from urllib.request import urlopen

url = "https://raw.githubusercontent.com/rw0104/apple-ui-skill/main/installer.py"
with urlopen(url, timeout=30) as response:
    if not response.geturl().startswith("https://"):
        raise SystemExit("Installer download must remain HTTPS.")
    data = response.read(1_000_001)
if len(data) > 1_000_000:
    raise SystemExit("Installer download exceeded the size limit.")
Path(sys.argv[1]).write_bytes(data)
PY
"$installer_python" "$installer_temp" "$@"
