import types
import sys
import unittest

from core import signals as signals_module
from core.twitch_emotes import get_manager, reset_manager


class TestEmoteSignalsLogging(unittest.TestCase):
    def test_extended_global_signal_payload(self):
        # Ensure a fresh manager picks up test stubbed http_session.
        # Install a module-level fake before resetting/creating the manager.
        fake_session = types.SimpleNamespace()

        def make_retry_session():
            return types.SimpleNamespace(get=lambda *a, **k: types.SimpleNamespace(status_code=200, json=lambda: {'data': []}, content=b''))

        fake_session.make_retry_session = make_retry_session
        sys.modules['core.http_session'] = fake_session

        # Reset module singleton so it uses the test stub
        reset_manager()

        mgr = get_manager()

        received = {}

        def on_ext(payload):
            received['payload'] = payload

        # Connect to the extended signal (works for PyQt or stub)
        try:
            signals_module.signals.emotes_global_warmed_ext.connect(on_ext)
        except Exception:
            # If attribute missing, fail the test
            self.fail('Extended global signal not available')

        # Synchronous prefetch to force emission
        mgr.prefetch_global(background=False)

        self.assertIn('payload', received)
        p = received['payload']
        self.assertIsInstance(p, dict)
        self.assertEqual(p.get('status'), 'ok')
        self.assertIn('timestamp', p)
        self.assertIn('emote_count', p)


if __name__ == '__main__':
    unittest.main()
