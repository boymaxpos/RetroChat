#!/bin/sh
set -eu

if [ "$(/usr/bin/id -u)" -ne 0 ]; then
    echo "Run this finalizer with sudo." >&2
    exit 1
fi

GROUP="com.apple.access_ssh"
AUTHORIZED_KEYS="/Users/retrochat/.ssh/authorized_keys"
EXPECTED_COMMENT="retrochat-phase7-temporary"

if ! /usr/sbin/dseditgroup -o checkmember -m retrochat "${GROUP}" 2>&1 \
    | /usr/bin/grep -q '^yes '; then
    echo "Refusing to remove existing access: retrochat is not in ${GROUP}." >&2
    exit 1
fi

if [ -e "${AUTHORIZED_KEYS}" ]; then
    if [ "$(/usr/bin/wc -l < "${AUTHORIZED_KEYS}" | /usr/bin/tr -d ' ')" != "1" ] \
        || ! /usr/bin/grep -q " ${EXPECTED_COMMENT}$" "${AUTHORIZED_KEYS}"; then
        echo "Refusing to remove an authorized_keys file not owned by this test." >&2
        exit 1
    fi
    /bin/rm "${AUTHORIZED_KEYS}"
fi

/usr/sbin/dseditgroup -o edit -d boymax -t user "${GROUP}"
/usr/sbin/dseditgroup -o edit -d admin -t group "${GROUP}" >/dev/null 2>&1 || true
/usr/bin/dscl . -create /Users/retrochat IsHidden 1

if /usr/sbin/dseditgroup -o checkmember -m boymax "${GROUP}" 2>&1 \
    | /usr/bin/grep -q '^yes '; then
    echo "Failed to remove boymax from ${GROUP}." >&2
    exit 1
fi

/usr/sbin/sshd -t
echo "Temporary key removed; Remote Login is restricted to retrochat."
