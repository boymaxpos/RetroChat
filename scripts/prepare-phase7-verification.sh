#!/bin/sh
set -eu

if [ "$(/usr/bin/id -u)" -ne 0 ]; then
    echo "Run this preparation with sudo." >&2
    exit 1
fi

TEST_PUBLIC_KEY=${1:-}
AUTHORIZED_KEYS="/Users/retrochat/.ssh/authorized_keys"
EXPECTED_COMMENT="retrochat-phase7-temporary"
ECDSA_PRIVATE="/etc/ssh/ssh_host_ecdsa_key"
ECDSA_PUBLIC="/etc/ssh/ssh_host_ecdsa_key.pub"
CODEX_SOURCE="/Users/boymax/.local/bin/codex"
CODEX_RUNTIME="/usr/local/libexec/retrochat/codex"

if [ ! -f "${TEST_PUBLIC_KEY}" ]; then
    echo "Temporary test public key not found: ${TEST_PUBLIC_KEY}" >&2
    exit 1
fi

if [ ! -x "${CODEX_SOURCE}" ]; then
    echo "Codex source executable not found: ${CODEX_SOURCE}" >&2
    exit 1
fi

if [ -e "${AUTHORIZED_KEYS}" ]; then
    if [ "$(/usr/bin/wc -l < "${AUTHORIZED_KEYS}" | /usr/bin/tr -d ' ')" != "1" ] \
        || ! /usr/bin/grep -q " ${EXPECTED_COMMENT}$" "${AUTHORIZED_KEYS}"; then
        echo "Refusing to replace an authorized_keys file not owned by this test." >&2
        exit 1
    fi
fi

/usr/bin/install -d -o retrochat -g staff -m 700 /Users/retrochat/.ssh
/usr/bin/install -o retrochat -g staff -m 600 \
    "${TEST_PUBLIC_KEY}" "${AUTHORIZED_KEYS}"
/usr/bin/install -o root -g wheel -m 755 \
    "${CODEX_SOURCE}" "${CODEX_RUNTIME}"
/usr/bin/install -o root -g wheel -m 755 \
    "$(CDPATH= cd -- "$(/usr/bin/dirname -- "$0")/.." && pwd)/deploy/retrochat-login" \
    /usr/local/bin/retrochat-login

if [ -f "${ECDSA_PRIVATE}" ]; then
    GENERATED_PUBLIC=$(/usr/bin/mktemp /private/tmp/retrochat-ecdsa-public.XXXXXX)
    PREVIOUS_PUBLIC=$(/usr/bin/mktemp /private/tmp/retrochat-ecdsa-previous.XXXXXX)
    VALIDATION_LOG=$(/usr/bin/mktemp /private/tmp/retrochat-sshd-validation.XXXXXX)
    trap '/bin/rm -f "${GENERATED_PUBLIC}" "${PREVIOUS_PUBLIC}" "${VALIDATION_LOG}"' EXIT HUP INT TERM
    /usr/bin/ssh-keygen -y -f "${ECDSA_PRIVATE}" > "${GENERATED_PUBLIC}"

    GENERATED_TYPE=$(/usr/bin/awk 'NR == 1 {print $1}' "${GENERATED_PUBLIC}")
    if [ "${GENERATED_TYPE}" != "ecdsa-sha2-nistp256" ]; then
        echo "Refusing to replace ECDSA public key: unexpected key type." >&2
        exit 1
    fi

    /usr/bin/ssh-keygen -lf "${GENERATED_PUBLIC}" >/dev/null
    /bin/cp -p "${ECDSA_PUBLIC}" "${PREVIOUS_PUBLIC}"

    /usr/bin/install -o root -g wheel -m 644 \
        "${GENERATED_PUBLIC}" "${ECDSA_PUBLIC}"

    if ! /usr/sbin/sshd -t 2>"${VALIDATION_LOG}" \
        || /usr/bin/grep -q "does not match private key" "${VALIDATION_LOG}"; then
        /usr/bin/install -o root -g wheel -m 644 \
            "${PREVIOUS_PUBLIC}" "${ECDSA_PUBLIC}"
        echo "OpenSSH validation failed; the previous ECDSA public key was restored." >&2
        /bin/cat "${VALIDATION_LOG}" >&2
        exit 1
    fi
fi

/usr/sbin/sshd -t
echo "Temporary key installed and OpenSSH validation passed."
