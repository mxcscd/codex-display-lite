# Restricted Codex Display — company MacBook Pro setup

Use this package instead of the earlier unrestricted setup ZIP.
The board runs protocol v2, advertised as **Codex Display Lite**.

1. Extract this entire folder into a permanent location on your company Mac.
2. Use your company-approved Codex app/CLI and company sign-in.
3. Have **CPython 3.13** installed; the bundled dependency wheels target that Python version on macOS.
4. Double-click **Start Codex Display.command**. It creates an isolated environment and installs only bundled wheels with exact version and SHA-256 checks. It does not download dependencies.
5. Power cycle the board with BOOT released. Allow Bluetooth access when requested. Verify that the Mac's pairing dialog refers to this display and enter the code shown on its screen.
6. Keep Terminal open and your Mac awake, online and nearby for fresh quota updates. Control-C stops the companion.

Only the company Mac needs to be paired. No background login service or global hooks are installed. No administrator, Accessibility, Automation, browser-cookie access or Full Disk Access permission is needed for the display code.

## Display layout

The cyan circular gauge and large central percentage show weekly quota remaining.
The outlined bottom panel shows short-window quota, short-window reset countdown,
weekly quota and weekly reset countdown. Focus and Refresh are compact buttons
above that panel. The side-button controls are unchanged.

`previews/gauge-preview.png` is rendered from the actual LVGL UI code with synthetic
example readings; it is not a photograph or a live company-account reading.
The 85%, 100% and offline layouts were rendered and inspected before flashing.

## Allowed data and behavior

- The companion starts the existing local Codex app-server over standard input/output. It does not open a listening server.
- Beyond initialization, its request allowlist contains only `account/rateLimits/read`.
- It extracts short-window and weekly remaining percentages and reset times. It does not call account usage history, list chats, or read transcript/hook files.
- Bluetooth sends only numeric quota fields, timestamps, validity flags, sequence number and protocol version. Missing or expired quotas show `--`.
- Only two device actions are accepted: **Focus Codex** and **Refresh Quota**. Extra fields, duplicate JSON keys, other actions and device-supplied app paths/arguments are rejected. Commands use encrypted BLE characteristics; duplicates are cached and repeated focus/refresh requests are rate-limited.
- Focus opens the locally selected Codex/ChatGPT app with `/usr/bin/open -a` and a fixed app path. No shell, AppleScript, keyboard events, typing, New Chat, or arbitrary command execution is provided.
- Refresh invokes the same quota-only read and pushes a new numeric snapshot. It does not list chats or access transcripts.
- On-screen buttons: **FOCUS CODEX** and **REFRESH QUOTA**. The side user button short press sends Focus; hold for one second sends Refresh. BOOT hold clears Bluetooth bonds; PWR controls power.
- The firmware exposes encrypted status, command and result characteristics, with only the two fixed actions. No Wi-Fi application or over-the-air update service is enabled.
- It does not write usage to persistent log files. `--once` intentionally prints one numeric snapshot for diagnosis.

## Residual risks for IT review

This is a modified open-source integration, not an independently audited or certified corporate product. Normal user permissions apply; it is not an OS sandbox. The existing Codex process still uses that user's account credentials and configuration, and a compromised dependency or modified local file could misuse user access. Package hashes check integrity, not publisher identity. Bluetooth/macOS, Python, Codex, the firmware and its dependencies remain trusted components. The owner confirmed the prior display-only screen worked. The new controls still need physical acceptance and pairing on the company Mac. A compromised paired device can trigger focus changes or repeated refreshes within the rate limits; it cannot choose arbitrary command arguments through this protocol.

Fixed dependencies reduce unexpected changes but still need reviewed updates for security fixes. BLE pairing does not establish manufacturer identity: verify the code on the physical display. The display reveals quota information to people who can see it.

If company software policy requires review, give IT this folder before running it. Do not bypass a corporate installation block.

To locate Codex manually:

```sh
CODEX_BIN='/full/path/to/codex' './Start Codex Display.command'
```

Original project: https://github.com/jayyao97/codex-usage-display (MIT).
