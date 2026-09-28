#!/bin/sh
# Deploy the ASCII-only Phase 10 interface without changing SSH or Codex auth.
set -eu

if [ "$(/usr/bin/id -u)" -ne 0 ]; then
    echo "Run with sudo: scripts/deploy-phase10-ui.sh" >&2
    exit 1
fi
if [ "$#" -ne 0 ]; then
    echo "This deployment script takes no arguments." >&2
    exit 1
fi

PROJECT_DIR=$(CDPATH= cd -- "$(/usr/bin/dirname -- "$0")/.." && pwd)
RUNTIME_DIR="/usr/local/libexec/retrochat"
LAUNCHER="/usr/local/bin/retrochat-login"
PYTHON="/opt/homebrew/bin/python3"

if [ ! -d "${RUNTIME_DIR}/retrochat" ] || [ ! -x "${RUNTIME_DIR}/codex" ] \
    || [ ! -f "${LAUNCHER}" ]; then
    echo "The restricted RetroChat runtime must already be installed." >&2
    exit 1
fi
if /usr/bin/pgrep -u retrochat -f 'from retrochat.app import main|retrochat.py' >/dev/null; then
    echo "Exit all RetroChat sessions with /exit, then run this again." >&2
    exit 1
fi

/bin/sh -n "${PROJECT_DIR}/deploy/retrochat-login"
STAGE=$(/usr/bin/mktemp -d /usr/local/libexec/retrochat-phase10-ui-stage.XXXXXX)
/usr/bin/install -d -o root -g wheel -m 755 "${STAGE}/retrochat"
for source in "${PROJECT_DIR}"/retrochat/*.py; do
    /usr/bin/install -o root -g wheel -m 644 \
        "${source}" "${STAGE}/retrochat/$(/usr/bin/basename "${source}")"
done
/usr/bin/install -o root -g wheel -m 755 \
    "${PROJECT_DIR}/deploy/retrochat-login" "${STAGE}/retrochat-login"

# Parse every staged module and verify the final banner at the byte boundary.
"${PYTHON}" -I -B -c '
import ast, pathlib, sys
stage = pathlib.Path(sys.argv[1])
for source in (stage / "retrochat").glob("*.py"):
    ast.parse(source.read_text(encoding="utf-8"))
sys.path.insert(0, str(stage))
from retrochat.ui import BANNER, HELP_TEXT, UI_WIDTH
BANNER.encode("ascii")
HELP_TEXT.encode("ascii")
assert all(len(line) <= UI_WIDTH for line in BANNER.splitlines())
assert all(len(line) <= UI_WIDTH for line in HELP_TEXT.splitlines())
assert "MAC GATEWAY ONLINE" in BANNER
from retrochat.app import main
' "${STAGE}"

BACKUP=$(/usr/bin/mktemp -d /usr/local/libexec/retrochat-phase10-ui-backup.XXXXXX)
/bin/cp -p "${LAUNCHER}" "${BACKUP}/retrochat-login"

# The baseline launcher works with both the previous and new package, so update
# it first and then replace the Python package as one directory rename.
/usr/bin/install -o root -g wheel -m 755 "${STAGE}/retrochat-login" "${LAUNCHER}"
/bin/mv "${RUNTIME_DIR}/retrochat" "${BACKUP}/installed-retrochat"
/bin/mv "${STAGE}/retrochat" "${RUNTIME_DIR}/retrochat"
if [ -f "${RUNTIME_DIR}/terminal.toml" ]; then
    /bin/mv "${RUNTIME_DIR}/terminal.toml" "${BACKUP}/installed-terminal.toml"
fi

echo "Phase 10 ASCII interface deployed."
echo "Previous runtime backed up at: ${BACKUP}"
echo "Reconnect PuTTY to inspect the new RetroChat screen."
