# Phase 7 security design

Status: deployed and verified on 2026-09-28.

## Goal

Create a non-admin macOS account named `retrochat` that can authenticate over
SSH and is forced directly into RetroChat. The account must not receive an
interactive shell, SSH forwarding, SFTP, or access to the `boymax` home
directory.

## Runtime layout

- `/usr/local/libexec/retrochat/` - root-owned application and Codex CLI copy
- `/usr/local/bin/retrochat-login` - root-owned launcher with a fixed environment
- `/Users/retrochat/.codex/` - user-owned Codex configuration and credentials
- `/etc/ssh/sshd_config.d/200-retrochat.conf` - root-owned per-user SSH policy

The launcher uses fixed paths for Python, Codex, and the RetroChat entry point.
It does not inherit `PYTHONPATH`, `CODEX_HOME`, `RETROCHAT_CODEX`, shell
startup configuration, or other caller-controlled execution settings.

## SSH policy

The installed OpenSSH include is:

```text
Match User retrochat
    ForceCommand /usr/local/bin/retrochat-login
    DisableForwarding yes
    PermitTTY yes
    PermitUserRC no
    MaxSessions 1
    MaxAuthTries 3
    ClientAliveInterval 300
    ClientAliveCountMax 2

Match all
```

`ForceCommand` ignores commands and subsystems requested by the client, so an
ordinary shell and SFTP are not exposed. `DisableForwarding` disables TCP,
Unix-socket, agent, and X11 forwarding. `PermitUserRC no` prevents
`~/.ssh/rc` from running. `Match all` is required because macOS includes the
fragment near the beginning of its main configuration file.

The complete configuration was validated before and after installation with:

```text
sshd -t
sshd -T -C user=retrochat,host=localhost,addr=127.0.0.1
```

Remote Login's allow-list now contains only `retrochat`. The `boymax` and nested
`admin` entries were removed after the new account passed its live login test.

## Account policy

- Standard local account, never administrator
- Login shell `/bin/sh`; no user-controlled shell startup file is loaded by the
  forced non-interactive command
- Hidden from the normal login window if macOS supports that without weakening
  account management
- Strong unique password entered only by the owner, never by RetroChat or Codex
- No Full Disk Access
- No Secure Token or APFS volume ownership. System Settings granted both when
  the account was created; they were explicitly removed after verification.

Password login is acceptable only for the initial LAN test. A PuTTY public key
and per-user public-key-only authentication should be considered during the
Windows 98 phase. Until then, port 22 should not be exposed beyond the trusted
LAN.

## Codex authentication

The `retrochat` account performed its own ChatGPT login with:

```text
codex login --device-auth
```

The owner completes the browser/device confirmation. RetroChat will not copy
`boymax`'s `~/.codex/auth.json`, request an API key, or print an OAuth token.
The dedicated account's credential cache is readable only by that account and
must be treated like a password.

Official authentication guidance:
https://developers.openai.com/codex/auth

## Remaining risks

- The SSH password can be guessed while password authentication is enabled.
- The macOS application firewall is currently disabled.
- The Codex login cache is a valuable credential owned by `retrochat`.
- RetroChat still launches Codex App Server. It uses a read-only sandbox,
  rejects server tool requests, and disables sandbox network access, but this is
  application-level defense rather than a separate OS sandbox.
- Anyone who can log in as `retrochat` can consume the linked ChatGPT account's
  Codex allowance and send conversation text to OpenAI.
- The Homebrew Python installation and the source Codex CLI are maintained by
  the admin user. Runtime updates must be deliberately redeployed as root.

## Verification

1. Confirmed `retrochat` is hidden, non-admin, and isolated from `/Users/boymax`.
2. Confirmed the installed `sshd` policy uses the forced command and disables
   forwarding.
3. Confirmed a requested remote command opens RetroChat instead of executing.
4. Confirmed SFTP and TCP forwarding fail.
5. Completed a real PTY conversation and received `PHASE7_OK` from the model.
6. Confirmed `/exit` closes the SSH session cleanly.
7. Confirmed Remote Login's allow-list contains only `retrochat`.
8. Confirmed the temporary verification public key no longer authenticates.
9. Confirmed password and keyboard-interactive authentication remain offered.
10. Confirmed `retrochat` has no Secure Token or APFS volume ownership.

## Rollback

1. Restore `boymax` in the Remote Login allow-list.
2. Remove `/etc/ssh/sshd_config.d/200-retrochat.conf` and validate OpenSSH.
3. Remove the root-owned launcher and runtime copy.
4. Revoke or log out the dedicated Codex credential.
5. Delete the `retrochat` account and home directory only with a separate,
   explicit destructive-action confirmation.
