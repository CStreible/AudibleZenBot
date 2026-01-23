import types
import sys
import unittest

class CyclingSession:
    def __init__(self, responses):
        # responses: list of status codes or response-like objects
        self._responses = list(responses)

    def get(self, *a, **k):
        if not self._responses:
            # default to 200 empty
            return types.SimpleNamespace(status_code=200, json=lambda: {'data': []}, content=b'')
        r = self._responses.pop(0)
        if isinstance(r, int):
            return types.SimpleNamespace(status_code=r, json=lambda: {'data': []}, content=b'')
        return r


class TestEmoteBackoff(unittest.TestCase):
    def test_prefetch_retries_on_429_then_succeeds(self):
        # Two 429 responses, then a 200
        cycling = CyclingSession([429, 429, 200])
        fake = types.SimpleNamespace()
        fake.make_retry_session = lambda: cycling
        sys.modules['core.http_session'] = fake

        # reload module so manager uses stubbed session
        import importlib
        import core.twitch_emotes as te
        importlib.reload(te)
        from core.twitch_emotes import get_manager

        mgr = get_manager()
        # speed up backoff for test
        mgr._backoff_base = 0.001

        received = {}
        from core import signals as signals_module

        def on_ext(payload):
            received['payload'] = payload

        signals_module.signals.emotes_global_warmed_ext.connect(on_ext)

        mgr.prefetch_global(background=False)

        self.assertIn('payload', received)
        p = received['payload']
        self.assertEqual(p.get('status'), 'ok')


if __name__ == '__main__':
    unittest.main()
