# Security boundaries

This is a private, modified open-source integration, not an independently audited or
certified company product. Follow company software and peripheral policies.

- The companion communicates with the existing Codex app-server over stdio; it opens no listening server.
- After initialization, its request allowlist contains only `account/rateLimits/read`.
- No chat listing, transcript/hook-file reads, browser cookie access, typing, keyboard shortcuts or AppleScript.
- Account credentials remain handled by the existing local Codex installation.
- BLE quota snapshots contain only numeric quota, reset, timing and validity fields.
- Device controls accept only `focus` and `refresh` with a strict JSON shape and bounded queues/caches.
- Focus launches a locally selected Codex/ChatGPT app using `/usr/bin/open -a`, without a shell.
- Refresh reads quota again. Requests are rate-limited and duplicate IDs are cached.
- Firmware command/status/result characteristics require encryption; verify the PIN on the physical display.
- No Wi-Fi application or OTA update service. Firmware updates use USB.
- No login service, global hooks or persistent usage logs are installed.
- Runtime dependencies are bundled and pinned by version and SHA-256. Hashes establish integrity, not publisher identity.

## Residual risks

Normal user permissions apply; this code is not an OS security sandbox. Compromised
local code, dependencies, Codex or the OS could misuse the user's access. A compromised
paired device can trigger app focus changes or quota refreshes within the rate limits.
Bluetooth device names and service UUIDs are not manufacturer authentication. Verify
the pairing code on the intended physical device. People near the screen can see quota.
Pinned dependencies still require reviewed updates for security fixes.

Do not commit credentials, auth.json, usage logs, device backups, company content,
private account output or local virtual environments. The bundled preview data is synthetic.

Report security concerns privately to the repository owner; do not post credentials
or exploit details in a public issue.
