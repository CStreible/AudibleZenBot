import unittest
import asyncio
from unittest.mock import patch, MagicMock

import scripts.manual.kickpython_direct as kpd


class FakeAPI:
    def __init__(self, *args, **kwargs):
        pass

    def _store_token(self, channel_id, access_token, refresh_token, expires_in, scope):
        # noop
        return None

    async def post_chat(self, channel_id, content):
        return {'status': 'ok'}

    async def close(self):
        return None


class TestKickPythonDirect(unittest.IsolatedAsyncioTestCase):
    @patch('scripts.manual.kickpython_direct.KickAPI', new=FakeAPI)
    async def test_test_send_runs(self):
        await kpd.test_send()


if __name__ == '__main__':
    unittest.main()
