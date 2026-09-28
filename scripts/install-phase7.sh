#!/bin/sh
set -eu

if [ "$(/usr/bin/id -u)" -ne 0 ]; then
    echo "Run this installer with sudo." >&2
    exit 1
fi

SCRIPT_DIR=$(CDPATH= cd -- "$(/usr/bin/dirname -- "$0")" && pwd)
PROJECT_DIR=$(CDPATH= cd -- "${SCRIPT_DIR}/.." && pwd)
RUNTIME_DIR="/usr/local/libexec/retrochat"
LAUNCHER="/usr/local/bin/retrochat-login"
SSHD_FRAGMENT="/etc/ssh/sshd_config.d/200-retrochat.conf"
TEST_PUBLIC_KEY=${1:-}
CODEX_SOURCE="/Users/boymax/.local/bin/codex"

if ! /usr/bin/id retrochat >/dev/null 2>&1; then
    echo "The retrochat account does not exist." >&2
    exit 1
fi

if /usr/sbin/dseditgroup -o checkmember -m retrochat admin 2>&1 \
    | /usr/bin/grep -q " is a member "; then
    echo "Refusing to install: retrochat is an administrator." >&2
    exit 1
fi

for required in \
    /opt/homebrew/bin/python3 \
    "${CODEX_SOURCE}" \
    "${PROJECT_DIR}/deploy/retrochat-login" \
    "${PROJECT_DIR}/deploy/retrochat-config.toml" \
    "${PROJECT_DIR}/deploy/200-retrochat.conf"; do
    if [ ! -e "${required}" ]; then
        echo "Missing required file: ${required}" >&2
        exit 1
    fi
done

if [ -e "${SSHD_FRAGMENT}" ]; then
    echo "Refusing to overwrite existing ${SSHD_FRAGMENT}." >&2
    exit 1
fi

/usr/bin/install -d -o root -g wheel -m 755 /usr/local/bin
/usr/bin/install -d -o root -g wheel -m 755 /usr/local/libexec
/usr/bin/install -d -o root -g wheel -m 755 "${RUNTIME_DIR}"
/usr/bin/install -d -o root -g wheel -m 755 "${RUNTIME_DIR}/retrochat"

/usr/bin/install -o root -g wheel -m 644 \
    "${PROJECT_DIR}/retrochat.py" "${RUNTIME_DIR}/retrochat.py"
/usr/bin/install -o root -g wheel -m 755 \
    "${CODEX_SOURCE}" "${RUNTIME_DIR}/codex"
for source in "${PROJECT_DIR}"/retrochat/*.py; do
    /usr/bin/install -o root -g wheel -m 644 \
        "${source}" "${RUNTIME_DIR}/retrochat/$(/usr/bin/basename "${source}")"
done
/usr/bin/install -o root -g wheel -m 755 \
    "${PROJECT_DIR}/deploy/retrochat-login" "${LAUNCHER}"

/usr/bin/install -o root -g wheel -m 644 \
    "${PROJECT_DIR}/deploy/200-retrochat.conf" "${SSHD_FRAGMENT}"
if ! /usr/sbin/sshd -t; then
    /bin/rm -f "${SSHD_FRAGMENT}"
    echo "OpenSSH validation failed; the new fragment was removed." >&2
    exit 1
fi

/usr/bin/dscl . -create /Users/retrochat UserShell /bin/sh
/usr/bin/dscl . -create /Users/retrochat IsHidden 1

/usr/bin/install -d -o retrochat -g staff -m 700 /Users/retrochat/.retrochat
/usr/bin/install -d -o retrochat -g staff -m 700 /Users/retrochat/.retrochat/tmp
/usr/bin/install -d -o retrochat -g staff -m 700 /Users/retrochat/.codex
/usr/bin/install -o retrochat -g staff -m 600 \
    "${PROJECT_DIR}/deploy/retrochat-config.toml" \
    /Users/retrochat/.codex/config.toml

if [ -n "${TEST_PUBLIC_KEY}" ]; then
    if [ ! -f "${TEST_PUBLIC_KEY}" ]; then
        echo "Temporary test public key not found: ${TEST_PUBLIC_KEY}" >&2
        exit 1
    fi
    if [ -e /Users/retrochat/.ssh/authorized_keys ]; then
        echo "Refusing to overwrite an existing authorized_keys file." >&2
        exit 1
    fi
    /usr/bin/install -d -o retrochat -g staff -m 700 /Users/retrochat/.ssh
    /usr/bin/install -o retrochat -g staff -m 600 \
        "${TEST_PUBLIC_KEY}" /Users/retrochat/.ssh/authorized_keys
fi

echo "Phase 7 runtime and SSH restriction installed."
echo "The Remote Login allow-list and Codex login are not changed by this script."
