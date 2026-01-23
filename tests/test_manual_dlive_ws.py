import unittest
import asyncio
from unittest.mock import patch

import scripts.manual.dlive as dlive


class FakeWS:
    def __init__(self):
        self.send_count = 0
        self.recv_count = 0

    async def send(self, data):
        self.send_count += 1

    async def recv(self):
        # First recv -> connection_ack
        if self.recv_count == 0:
            self.recv_count += 1
            return '{"type": "connection_ack"}'

        # For the two immediate wait_for checks, simulate timeout by raising
        if self.recv_count in (1, 2):
            self.recv_count += 1
            raise asyncio.TimeoutError()

        # For the main listen loop, raise KeyboardInterrupt to exit cleanly
        raise KeyboardInterrupt()


class FakeConnect:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return FakeWS()

    async def __aexit__(self, exc_type, exc, tb):
        return False


class TestDLiveWS(unittest.IsolatedAsyncioTestCase):
    @patch('scripts.manual.dlive.websockets.connect', new=FakeConnect)
    async def test_test_connection_runs_and_exits(self):
        # Should complete without unhandled exceptions
        await dlive.test_connection()


if __name__ == '__main__':
    unittest.main()
