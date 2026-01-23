import unittest
from unittest.mock import patch, MagicMock, ANY

import scripts.manual.kick_token_scopes as kts


class TestKickTokenScopes(unittest.TestCase):
    @patch('scripts.manual.kick_token_scopes.requests.post')
    @patch('scripts.manual.kick_token_scopes.requests.get')
    def test_main_happy_path(self, mock_get, mock_post):
        fake_get = MagicMock()
        fake_get.status_code = 200
        fake_get.text = '[]'
        fake_get.json.return_value = {'data': [{'slug': 'test', 'broadcaster_user_id': '1'}]}
        mock_get.return_value = fake_get

        fake_post = MagicMock()
        fake_post.status_code = 200
        fake_post.text = 'ok'
        mock_post.return_value = fake_post

        # Run main; should call get and post
        kts.main()

        self.assertTrue(mock_get.called)
        self.assertTrue(mock_post.called)
        mock_post.assert_called_with('https://api.kick.com/public/v1/chat', headers=ANY, json=ANY, timeout=10)


if __name__ == '__main__':
    unittest.main()
