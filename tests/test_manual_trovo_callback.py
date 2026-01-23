import unittest
from unittest.mock import Mock, patch


class TestManualTrovoCallback(unittest.TestCase):
    def test_trovo_callback_uses_make_retry_session_if_available(self):
        # Prepare a fake session whose get() we can observe
        fake_session = Mock()
        fake_response = Mock()
        fake_response.status_code = 200
        fake_response.text = 'ok'
        fake_session.get.return_value = fake_response

        # Patch the module's make_retry_session to return our fake session
        from scripts.manual.platform_connectors import trovo_callback
        with patch.object(trovo_callback, 'make_retry_session', lambda: fake_session):
            # Call main, which should use the fake_session
            trovo_callback.main()

        fake_session.get.assert_called()


if __name__ == '__main__':
    unittest.main()
