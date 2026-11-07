"""Two fixed actions. No keyboard events, AppleScript, shell, or device arguments."""
import asyncio
import json
import time
from pathlib import Path


def find_focus_app(codex_binary):
    binary = Path(codex_binary).expanduser().resolve()
    for parent in binary.parents:
        if parent.name in {"Codex.app", "ChatGPT.app"} and parent.is_dir():
            return str(parent)
    for directory in [Path("/Applications"), Path.home() / "Applications"]:
        for name in ["Codex.app", "ChatGPT.app"]:
            candidate = directory / name
            if candidate.is_dir():
                return str(candidate)
    return None


def decode_command(data):
    if len(data) > 128:
        raise ValueError("Invalid command")
    def unique_keys(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("Duplicate field")
            value[key] = item
        return value
    try:
        command = json.loads(data.decode("ascii"), object_pairs_hook=unique_keys)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("Invalid command") from error
    if not isinstance(command, dict) or set(command) != {"v", "sid", "id", "a"}:
        raise ValueError("Invalid fields")
    if type(command["v"]) is not int or command["v"] != 2:
        raise ValueError("Invalid version")
    if any(type(command[k]) is not int or not 1 <= command[k] <= 0xFFFFFFFF for k in ["sid", "id"]):
        raise ValueError("Invalid identity")
    if command["a"] not in ("focus", "refresh"):
        raise ValueError("Action disabled")
    return command


class Controls:
    def __init__(self, refresh, focus_app):
        self.refresh = refresh
        self.focus_app = focus_app
        self.recent = {}
        self.last_action = {}

    async def handle(self, data):
        command = decode_command(data)
        key = (command["sid"], command["id"])
        if key in self.recent:
            return self.recent[key]
        action = command["a"]
        now = time.monotonic()
        interval = 10 if action == "refresh" else 2
        ok, message = False, "WAIT BEFORE RETRY"
        if now - self.last_action.get(action, -float("inf")) >= interval:
            self.last_action[action] = now
            if action == "refresh":
                try:
                    await self.refresh()
                    ok, message = True, "QUOTA REFRESHED"
                except Exception:
                    message = "REFRESH FAILED"
            elif self.focus_app is None:
                message = "CODEX APP NOT FOUND"
            else:
                # The app path is selected locally, never supplied over Bluetooth.
                process = await asyncio.create_subprocess_exec(
                    "/usr/bin/open", "-a", self.focus_app,
                    stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
                try:
                    code = await asyncio.wait_for(process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
                    code = 1
                ok, message = (True, "CODEX FOCUSED") if code == 0 else (False, "FOCUS FAILED")
        payload = json.dumps({"v": 2, "id": command["id"], "ok": int(ok), "m": message}, separators=(",", ":")).encode("ascii")
        self.recent[key] = payload
        if len(self.recent) > 32:
            del self.recent[next(iter(self.recent))]
        return payload
