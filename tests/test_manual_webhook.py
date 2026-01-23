import unittest
from unittest.mock import patch, Mock


class TestManualWebhook(unittest.TestCase):
    @patch('scripts.manual.webhook.requests.get')
    @patch('scripts.manual.webhook.requests.post')
    def test_webhook_main_calls_get_and_post(self, mock_post, mock_get):
        # Arrange: make both calls return a mock response
        r_get = Mock()
        r_get.status_code = 200
        r_get.text = 'OK'
        mock_get.return_value = r_get

        r_post = Mock()
        r_post.status_code = 200
        r_post.text = 'Posted'
        mock_post.return_value = r_post

        # Act: import and call main
        from scripts.manual import webhook
        webhook.main()

        # Assert: both were called
        mock_get.assert_called()
        mock_post.assert_called()


if __name__ == '__main__':
    unittest.main()
