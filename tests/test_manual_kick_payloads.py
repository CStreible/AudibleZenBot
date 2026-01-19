import unittest
from unittest.mock import patch, MagicMock, ANY

import scripts.manual.kick_payloads as kp


class TestKickPayloads(unittest.TestCase):
    @patch('scripts.manual.kick_payloads.requests.post')
    def test_various_payloads_send(self, mock_post):
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.text = 'ok'
        mock_post.return_value = fake_resp

        kp.main()

        self.assertTrue(mock_post.called)
        # verify it attempted the public chat endpoint
        mock_post.assert_any_call('https://api.kick.com/public/v1/chat', headers=ANY, json=ANY, timeout=10)


if __name__ == '__main__':
    unittest.main()
