import unittest
from unittest.mock import patch, MagicMock

import scripts.manual.dlive_http as dlive


class TestDLiveHttp(unittest.TestCase):
    @patch('scripts.manual.dlive_http.requests.post')
    def test_query_user_success(self, mock_post):
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = {
            'data': {
                'userByDisplayName': {
                    'id': '123',
                    'username': 'audiblezen',
                    'displayname': 'AudibleZen',
                    'livestream': {
                        'id': 's1',
                        'title': 'Test Stream',
                        'watchingCount': 5
                    }
                }
            }
        }

        mock_post.return_value = fake_resp

        # Should run without raising and call requests.post
        dlive.query_user()

        mock_post.assert_called_once()
        self.assertTrue(fake_resp.json.called)


if __name__ == '__main__':
    unittest.main()
