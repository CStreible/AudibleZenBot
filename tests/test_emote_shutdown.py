import threading
import types
import sys
import unittest


class TestEmoteShutdown(unittest.TestCase):
    def test_shutdown_clears_prefetch_threads(self):
        # Inject a minimal core.http_session module so importing
        # core.twitch_emotes does not require external `requests`.
        fake_session = types.SimpleNamespace()

        def make_retry_session():
            # session.get should be callable; return a dummy response
            return types.SimpleNamespace(get=lambda *a, **k: types.SimpleNamespace(status_code=200, json=lambda: {'data': []}, content=b''))

        fake_session.make_retry_session = make_retry_session
        sys.modules['core.http_session'] = fake_session

        # Now import manager (after stubbing http_session)
        from core.twitch_emotes import get_manager

        mgr = get_manager()

        # Create small dummy objects that mimic thread-like APIs
        class DummyThreadLike:
            def join(self, timeout=None):
                return None

            def quit(self):
                return None

            def wait(self, t=None):
                return None

        dummy1 = DummyThreadLike()
        # A real threading.Thread that is not started (join returns immediately)
        dummy2 = threading.Thread(target=lambda: None)

        mgr._prefetch_threads = [dummy1, dummy2]

        # Call shutdown and ensure the list is cleared
        mgr.shutdown(timeout=0.01)

        self.assertEqual(getattr(mgr, '_prefetch_threads', []), [])


if __name__ == '__main__':
    unittest.main()
