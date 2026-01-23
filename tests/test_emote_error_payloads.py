import types
import sys
import unittest

def make_session_429():
    return types.SimpleNamespace(get=lambda *a, **k: types.SimpleNamespace(status_code=429, json=lambda: {'data': []}, content=b''))

def make_session_network_error():
    def _get(*a, **k):
        raise Exception('connection failure')

    return types.SimpleNamespace(get=_get)


class TestEmoteErrorPayloads(unittest.TestCase):
    def test_rate_limited_payload(self):
        # Stub http_session to simulate 429
        fake = types.SimpleNamespace()
        fake.make_retry_session = lambda: make_session_429()
        sys.modules['core.http_session'] = fake

        from core import signals as signals_module
        # Reload module so manager singleton picks up our stubbed session
        import importlib
        import core.twitch_emotes as te
        importlib.reload(te)
        from core.twitch_emotes import get_manager

        mgr = get_manager()

        received = {}

        def on_ext(payload):
            received['payload'] = payload

        # Connect to extended signal
        signals_module.signals.emotes_global_warmed_ext.connect(on_ext)

        mgr.prefetch_global(background=False)

        self.assertIn('payload', received)
        p = received['payload']
        self.assertEqual(p.get('status'), 'error')
        self.assertEqual(p.get('error_code'), 'rate_limited')

    def test_network_payload(self):
        # Stub http_session to simulate network error
        fake = types.SimpleNamespace()
        fake.make_retry_session = lambda: make_session_network_error()
        sys.modules['core.http_session'] = fake

        from core import signals as signals_module
        # Reload module so manager singleton picks up our stubbed session
        import importlib
        import core.twitch_emotes as te
        importlib.reload(te)
        from core.twitch_emotes import get_manager

        mgr = get_manager()

        received = {}

        def on_ext(payload):
            received['payload'] = payload

        signals_module.signals.emotes_global_warmed_ext.connect(on_ext)

        mgr.prefetch_global(background=False)

        self.assertIn('payload', received)
        p = received['payload']
        self.assertEqual(p.get('status'), 'error')
        self.assertIn(p.get('error_code'), ('network', 'exception'))

    def test_channel_rate_limited_payload(self):
        fake = types.SimpleNamespace()
        fake.make_retry_session = lambda: make_session_429()
        sys.modules['core.http_session'] = fake

        from core import signals as signals_module
        import importlib
        import core.twitch_emotes as te
        importlib.reload(te)
        from core.twitch_emotes import get_manager

        mgr = get_manager()

        received = {}

        def on_ext(payload):
            received['payload'] = payload

        signals_module.signals.emotes_channel_warmed_ext.connect(on_ext)

        mgr.prefetch_channel('12345', background=False)

        self.assertIn('payload', received)
        p = received['payload']
        self.assertEqual(p.get('status'), 'error')
        self.assertEqual(p.get('error_code'), 'rate_limited')

    def test_channel_network_payload(self):
        fake = types.SimpleNamespace()
        fake.make_retry_session = lambda: make_session_network_error()
        sys.modules['core.http_session'] = fake

        from core import signals as signals_module
        import importlib
        import core.twitch_emotes as te
        importlib.reload(te)
        from core.twitch_emotes import get_manager

        mgr = get_manager()

        received = {}

        def on_ext(payload):
            received['payload'] = payload

        signals_module.signals.emotes_channel_warmed_ext.connect(on_ext)

        mgr.prefetch_channel('12345', background=False)

        self.assertIn('payload', received)
        p = received['payload']
        self.assertEqual(p.get('status'), 'error')
        self.assertIn(p.get('error_code'), ('network', 'exception'))


if __name__ == '__main__':
    unittest.main()
