import asyncio
import logging
from typing import Any, Awaitable, Callable, Optional

from .constants import (
    DEVICE_NAME,
    SERVICE_UUID,
    STATUS_UUID,
    COMMAND_UUID,
    RESULT_UUID,
)

logger = logging.getLogger(__name__)

BLE_OPERATION_TIMEOUT_SECONDS = 10
BLE_DISCONNECT_TIMEOUT_SECONDS = 5


class BleCompanion:
    def __init__(
        self,
        get_status: Callable[[], Awaitable[bytes]],
        request_refresh: Callable[[], Awaitable[None]],
        device_name: str = DEVICE_NAME,
        heartbeat_seconds: float = 15,
        status_changed: Optional[asyncio.Event] = None,
        controls=None,
    ) -> None:
        self._get_status = get_status
        self._request_refresh = request_refresh
        self._device_name = device_name
        self._heartbeat_seconds = heartbeat_seconds
        self._status_changed = status_changed
        self.connected_event = asyncio.Event()
        self._controls = controls

    async def run_forever(self) -> None:
        from bleak import BleakClient, BleakScanner

        backoff = 1.0
        while True:
            try:
                logger.info("Scanning for %s...", self._device_name)
                device = await BleakScanner.find_device_by_filter(
                    lambda candidate, advertisement: (
                        (candidate.name or "") == self._device_name
                        and SERVICE_UUID.lower()
                        in [uuid.lower() for uuid in advertisement.service_uuids]
                    ),
                    timeout=10,
                    service_uuids=[SERVICE_UUID],
                )
            except asyncio.CancelledError:
                raise
            except Exception as error:
                self.connected_event.clear()
                if "turned off" in str(error).lower():
                    logger.error(
                        "Bluetooth is unavailable or permission is missing; "
                        "check System Settings > Privacy & Security > Bluetooth"
                    )
                else:
                    logger.warning("BLE scan failed")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)
                continue
            if device is None:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)
                continue

            disconnected = asyncio.Event()

            def on_disconnect(_: Any) -> None:
                self.connected_event.clear()
                disconnected.set()

            client = BleakClient(
                device, disconnected_callback=on_disconnect
            )
            try:
                await client.connect()
                backoff = 1.0
                logger.info("Connected to %s", device.name or device.address)
                await self._run_connection(client, disconnected)
            except asyncio.CancelledError:
                raise
            except Exception as error:
                logger.warning("BLE connection interrupted")
            finally:
                self.connected_event.clear()
                await self._disconnect(client)

            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)

    async def _disconnect(self, client: Any) -> None:
        if not client.is_connected:
            return
        try:
            await asyncio.wait_for(
                client.disconnect(),
                timeout=BLE_DISCONNECT_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.warning("BLE disconnect timed out; resuming scan")
        except Exception as error:
            logger.warning("BLE disconnect failed")

    async def _run_connection(
        self, client: Any, disconnected: asyncio.Event
    ) -> None:
        commands = asyncio.Queue(maxsize=8)
        def on_command(_, data):
            if len(data) <= 128 and not commands.full():
                commands.put_nowait(bytes(data))

        await self._request_refresh()
        await self._send_status(client)
        if disconnected.is_set() or not client.is_connected:
            return
        self.connected_event.set()
        if self._controls is not None:
            # Subscribe only after the encrypted status write has succeeded.
            await client.start_notify(COMMAND_UUID, on_command)

        heartbeat = asyncio.create_task(self._heartbeat_loop(client))
        wait_disconnect = asyncio.create_task(disconnected.wait())
        tasks = [heartbeat, wait_disconnect]
        if self._controls is not None:
            tasks.append(asyncio.create_task(self._control_loop(client, commands)))
        try:
            done, pending = await asyncio.wait(
                tasks,
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            for task in done:
                if task is not wait_disconnect:
                    task.result()
        finally:
            self.connected_event.clear()
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _heartbeat_loop(self, client: Any) -> None:
        while client.is_connected:
            if self._status_changed is None:
                await asyncio.sleep(self._heartbeat_seconds)
            else:
                try:
                    await asyncio.wait_for(
                        self._status_changed.wait(),
                        timeout=self._heartbeat_seconds,
                    )
                except asyncio.TimeoutError:
                    pass
                self._status_changed.clear()
            await self._send_status(client)

    async def _control_loop(self, client, commands):
        while client.is_connected:
            raw = await commands.get()
            try:
                result = await self._controls.handle(raw)
            except ValueError:
                continue
            await self._write_gatt_char(client, RESULT_UUID, result)
            await self._send_status(client)

    async def _send_status(self, client: Any) -> None:
        payload = await self._get_status()
        await self._write_gatt_char(client, STATUS_UUID, payload)

    async def _write_gatt_char(
        self, client: Any, uuid: str, payload: bytes
    ) -> None:
        try:
            await asyncio.wait_for(
                client.write_gatt_char(
                    uuid,
                    payload,
                    response=True,
                ),
                timeout=BLE_OPERATION_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError as error:
            raise asyncio.TimeoutError("BLE GATT write timed out") from error
