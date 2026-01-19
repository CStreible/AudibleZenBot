import unittest
import asyncio
from unittest.mock import patch, MagicMock, ANY

import scripts.manual.kickpython_with_config as kpwc


class FakeAPI:
    def __init__(self, *args, **kwargs):
        pass

    async def get_broadcaster_id(self, token):
        return '123'

    async def get_chatroom_id(self, username):
        return ('456', {'slug': username})

    def _store_token(self, channel_id, access_token, refresh_token, expires_in, scope):
        return None

    async def post_chat(self, channel_id, content):
        return {'status': 'ok'}

    async def close(self):
        return None


class DummyPath:
    @classmethod
    def home(cls):
        return cls()

    def __truediv__(self, other):
        return self

    def open(self, *args, **kwargs):
        # Not actually used because json.load will be patched
        raise FileNotFoundError()


class TestKickPythonWithConfig(unittest.IsolatedAsyncioTestCase):
    @patch('scripts.manual.kickpython_with_config.json.load')
    @patch('pathlib.Path', new=DummyPath)
    @patch('scripts.manual.kickpython_with_config.KickAPI', new=FakeAPI)
    async def test_test_send_runs_with_config(self, mock_json_load):
        mock_json_load.return_value = {
            'platforms': {
                'kick': {
                    'streamer_token': 'tok',
                    'streamer_username': 'user',
                    'streamer_user_id': '123'
                }
            }
        }

        await kpwc.test_send()


if __name__ == '__main__':
    unittest.main()
