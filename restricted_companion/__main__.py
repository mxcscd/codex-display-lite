"""Read quota only; publish an allowlisted numeric snapshot over BLE."""
import argparse
import asyncio
import json
import logging
import math
import time

from .app_server import AppServerClient
from .ble import BleCompanion
from .controls import Controls, find_focus_app


def window(value, now):
    if not isinstance(value, dict):
        return 0, 0, False
    used, resets = value.get("usedPercent"), value.get("resetsAt")
    if (isinstance(used, bool) or not isinstance(used, (int, float))
            or not math.isfinite(used) or not 0 <= used <= 100
            or isinstance(resets, bool) or not isinstance(resets, int)
            or not now < resets <= now + 366 * 86400):
        return 0, 0, False
    return round(100 - used), resets, True


class QuotaCache:
    def __init__(self, client):
        self.client = client
        self.sampled = None
        self.primary = (0, 0, False)
        self.weekly = (0, 0, False)
        self.sequence = 0
        self.refreshed = 0.0

    async def refresh(self):
        result = await self.client.request("account/rateLimits/read")
        now = int(time.time())
        limits_by_id = result.get("rateLimitsByLimitId") or {}
        limits = limits_by_id.get("codex") or result.get("rateLimits") or {}
        self.primary = window(limits.get("primary"), now)
        self.weekly = window(limits.get("secondary"), now)
        self.sampled = now
        self.refreshed = time.monotonic()
        logging.info("Quota sample refreshed")

    async def encoded(self):
        if self.sampled is None or time.monotonic() - self.refreshed >= 60:
            await self.refresh()
        now = int(time.time())
        self.sequence = self.sequence % 0xFFFFFFFF + 1
        local = time.localtime(now)
        offset = -(time.altzone if local.tm_isdst > 0 and time.daylight else time.timezone) // 60
        p, pq, pv = self.primary
        w, wq, wv = self.weekly
        # Expired quotas remain unknown until the next successful provider read.
        payload = {"v": 2, "s": self.sequence, "t": now, "o": offset,
                   "p": p, "pq": max(0, pq - now), "pv": int(pv and pq > now),
                   "w": w, "wq": max(0, wq - now), "wv": int(wv and wq > now),
                   "age": max(0, now - self.sampled)}
        return json.dumps(payload, separators=(",", ":")).encode("ascii")


async def run(args):
    client = AppServerClient(args.codex_bin)
    try:
        await client.start()
        cache = QuotaCache(client)
        if args.once:
            print((await cache.encoded()).decode("ascii"))
            return
        controls = Controls(cache.refresh, find_focus_app(client._codex_binary))
        companion = BleCompanion(cache.encoded, cache.refresh, controls=controls)
        tasks = [asyncio.create_task(companion.run_forever()),
                 asyncio.create_task(client.wait_for_exit())]
        try:
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                task.result()
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        await client.stop()


def main():
    parser = argparse.ArgumentParser(description="Restricted Codex quota companion: Focus and Refresh only")
    parser.add_argument("--codex-bin")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        pass
    except Exception:
        # Do not emit raw account/server error text or snapshots to persistent logs.
        logging.error("Companion stopped. Check Codex sign-in and Bluetooth access.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
