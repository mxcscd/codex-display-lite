# Project boundaries

This repository is the restricted variant of the Waveshare Codex display.
Read README.md, MACBOOK_PRO_SETUP.md and SECURITY.md before setup changes.

Preserve these requirements unless the owner explicitly requests a scope change:
- Account RPC allowlist: initialization and account/rateLimits/read only.
- No chat listing, transcript/hook scanning, browser cookies, keyboard automation or AppleScript.
- Device actions: only fixed Focus Codex and Refresh Quota; never device-supplied paths or arguments.
- Preserve encrypted BLE pairing, bounded queues, replay deduplication and rate limits.
- Keep exact-hash offline runtime installation and exclude credentials/logs/backups/environments.
- The board is already flashed. Do not reflash as part of ordinary Mac setup.
- Follow the company's installation restrictions; do not bypass an administrative block.

Run the focused tests for companion changes. For firmware UI changes, build and
inspect the layout; do not describe simulator output as physical verification.
Never commit company credentials or personal usage data.
