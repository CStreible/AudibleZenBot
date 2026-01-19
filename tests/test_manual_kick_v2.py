import unittest
from unittest.mock import patch, MagicMock, ANY

import scripts.manual.kick_v2 as kick


class TestKickV2(unittest.TestCase):
    @patch('scripts.manual.kick_v2.requests.post')
    def test_main_stops_on_success(self, mock_post):
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.text = 'ok'
        mock_post.return_value = fake_resp

        # Should run without raising and call requests.post for endpoints
        kick.main()

        self.assertTrue(mock_post.called)
        # Ensure at least one of the known v2 URLs was attempted
        mock_post.assert_any_call('https://api.kick.com/v2/chat', headers=ANY, json=ANY, timeout=10)


if __name__ == '__main__':
    unittest.main()
