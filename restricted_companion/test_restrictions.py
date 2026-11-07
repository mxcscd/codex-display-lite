import asyncio
import json
import unittest
from unittest.mock import AsyncMock, patch

from .app_server import AppServerClient, AppServerError
from .ble import BleCompanion
from .constants import STATUS_UUID
from .__main__ import QuotaCache, window
from .controls import Controls, decode_command
from .constants import COMMAND_UUID


class RestrictionsTests(unittest.IsolatedAsyncioTestCase):
    async def test_account_actions_threads_and_usage_are_rejected_before_send(self):
        client = AppServerClient("unused")
        client._send = AsyncMock()
        for method in ["thread/list", "thread/start", "account/usage/read", "account/login/start", "exec"]:
            with self.assertRaises(AppServerError):
                await client.request(method)
        with self.assertRaises(AppServerError):
            await client.notify("anything", {})
        client._send.assert_not_awaited()

    async def test_quota_payload_excludes_identity_credits_and_unknown_fields(self):
        client = AsyncMock()
        client.request.return_value = {"rateLimitsByLimitId": {"codex": {
            "primary": {"usedPercent": 25, "resetsAt": 1200},
            "secondary": {"usedPercent": 60, "resetsAt": 8000},
            "email": "private@example.test", "tokens": "secret"}},
            "rateLimitResetCredits": {"availableCount": 99}}
        cache = QuotaCache(client)
        with patch("restricted_companion.__main__.time.time", return_value=1000):
            payload = json.loads(await cache.encoded())
        client.request.assert_awaited_once_with("account/rateLimits/read")
        self.assertEqual(set(payload), {"v", "s", "t", "o", "p", "pq", "pv", "w", "wq", "wv", "age"})
        self.assertEqual((payload["p"], payload["w"]), (75, 40))
        self.assertTrue(all(type(v) is int for v in payload.values()))

    async def test_missing_quota_remains_unknown(self):
        client = AsyncMock()
        client.request.return_value = {}
        payload = json.loads(await QuotaCache(client).encoded())
        self.assertEqual((payload["pv"], payload["wv"]), (0, 0))

    async def test_heartbeat_preserves_sample_age_and_expires_quota(self):
        client = AsyncMock()
        client.request.return_value = {"rateLimits": {"primary": {"usedPercent": 25, "resetsAt": 1005}}}
        cache = QuotaCache(client)
        with patch("restricted_companion.__main__.time.time", return_value=1000):
            first = json.loads(await cache.encoded())
        with patch("restricted_companion.__main__.time.time", return_value=1010):
            later = json.loads(await cache.encoded())
        self.assertEqual(later["age"], 10)
        self.assertEqual(later["pv"], 0)
        self.assertGreater(later["s"], first["s"])
        client.request.assert_awaited_once()

    async def test_failed_refresh_does_not_publish_fresh_looking_cached_data(self):
        client = AsyncMock()
        client.request.side_effect = RuntimeError("private provider failure")
        with self.assertRaises(RuntimeError):
            await QuotaCache(client).encoded()

    async def test_without_controls_has_no_command_subscription(self):
        client = AsyncMock()
        client.is_connected = False
        disconnected = asyncio.Event()
        disconnected.set()
        companion = BleCompanion(AsyncMock(return_value=b"{}"), AsyncMock())
        await companion._run_connection(client, disconnected)
        client.start_notify.assert_not_awaited()
        client.read_gatt_char.assert_not_awaited()
        client.write_gatt_char.assert_awaited_once_with(STATUS_UUID, b"{}", response=True)

    async def test_malformed_numeric_quota_is_unknown(self):
        for used in [True, "40", float("nan"), float("inf"), -1, 101]:
            self.assertEqual(window({"usedPercent": used, "resetsAt": 2000}, 1000), (0, 0, False))

    async def test_disallowed_actions_and_device_arguments_cannot_run(self):
        controls = Controls(AsyncMock(), "/Applications/Codex.app")
        invalid = [
            b'{"v":2,"sid":1,"id":1,"a":"new_task"}',
            b'{"v":2,"sid":1,"id":1,"a":"keystroke"}',
            b'{"v":2,"sid":1,"id":1,"a":"focus","path":"/tmp/other.app"}',
            b'{"v":2,"sid":1,"id":1,"a":"focus","a":"refresh"}',
            b'{"v":2,"sid":true,"id":1,"a":"focus"}',
            b'[]', b'x' * 129,
        ]
        with patch("restricted_companion.controls.asyncio.create_subprocess_exec", new_callable=AsyncMock) as launch:
            for data in invalid:
                with self.assertRaises(ValueError):
                    await controls.handle(data)
            launch.assert_not_awaited()
        controls.refresh.assert_not_awaited()

    async def test_focus_only_opens_locally_selected_application(self):
        process = AsyncMock()
        process.wait.return_value = 0
        controls = Controls(AsyncMock(), "/Applications/Codex.app")
        with patch("restricted_companion.controls.asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=process) as launch:
            result = json.loads(await controls.handle(b'{"v":2,"sid":1,"id":1,"a":"focus"}'))
        self.assertEqual(launch.call_args.args, ("/usr/bin/open", "-a", "/Applications/Codex.app"))
        self.assertNotIn("shell", launch.call_args.kwargs)
        self.assertEqual(result["ok"], 1)
        controls.refresh.assert_not_awaited()

    async def test_refresh_never_launches_a_process_and_duplicate_is_not_repeated(self):
        refresh = AsyncMock()
        controls = Controls(refresh, None)
        command = b'{"v":2,"sid":1,"id":1,"a":"refresh"}'
        with patch("restricted_companion.controls.asyncio.create_subprocess_exec", new_callable=AsyncMock) as launch:
            first = await controls.handle(command)
            self.assertEqual(await controls.handle(command), first)
            launch.assert_not_awaited()
        refresh.assert_awaited_once()

    async def test_refresh_is_rate_limited_and_cache_is_bounded(self):
        refresh = AsyncMock()
        controls = Controls(refresh, None)
        with patch("restricted_companion.controls.time.monotonic", return_value=100):
            for request_id in range(1, 50):
                result = json.loads(await controls.handle(json.dumps({"v":2,"sid":1,"id":request_id,"a":"refresh"}).encode()))
                if request_id > 1:
                    self.assertEqual(result["ok"], 0)
        refresh.assert_awaited_once()
        self.assertLessEqual(len(controls.recent), 32)

    async def test_raw_provider_errors_are_not_returned_to_device(self):
        controls = Controls(AsyncMock(side_effect=RuntimeError("secret credential")), None)
        result = await controls.handle(b'{"v":2,"sid":1,"id":1,"a":"refresh"}')
        self.assertNotIn(b"secret", result)
        self.assertEqual(json.loads(result)["m"], "REFRESH FAILED")

    async def test_control_subscription_follows_encrypted_status_write(self):
        order = []
        client = AsyncMock()
        client.is_connected = True
        async def write(*args, **kwargs):
            order.append("status")
        async def subscribe(*args, **kwargs):
            order.append("subscribe")
            disconnected.set()
        client.write_gatt_char.side_effect = write
        client.start_notify.side_effect = subscribe
        disconnected = asyncio.Event()
        companion = BleCompanion(AsyncMock(return_value=b"{}"), AsyncMock(), controls=Controls(AsyncMock(), None))
        await companion._run_connection(client, disconnected)
        self.assertEqual(order[:2], ["status", "subscribe"])
        self.assertEqual(client.start_notify.call_args.args[0], COMMAND_UUID)


if __name__ == "__main__":
    unittest.main()
