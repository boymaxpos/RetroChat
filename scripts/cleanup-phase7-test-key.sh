#!/bin/sh
set -eu

if [ "$(/usr/bin/id -u)" -ne 0 ]; then
    echo "Run this cleanup with sudo." >&2
    exit 1
fi

AUTHORIZED_KEYS="/Users/retrochat/.ssh/authorized_keys"
EXPECTED_COMMENT="retrochat-phase7-temporary"

if [ ! -e "${AUTHORIZED_KEYS}" ]; then
    echo "Temporary authorized_keys is already absent."
    exit 0
fi

if [ "$(/usr/bin/wc -l < "${AUTHORIZED_KEYS}" | /usr/bin/tr -d ' ')" != "1" ] \
    || ! /usr/bin/grep -q " ${EXPECTED_COMMENT}$" "${AUTHORIZED_KEYS}"; then
    echo "Refusing to remove an authorized_keys file not owned by this test." >&2
    exit 1
fi

/bin/rm "${AUTHORIZED_KEYS}"
echo "Temporary Phase 7 SSH public key removed."
