import types
import sys
import unittest

class CyclingSession:
    def __init__(self, responses):
        self._responses = list(responses)

    def get(self, *a, **k):
        if not self._responses:
            return types.SimpleNamespace(status_code=200, json=lambda: {'data': []}, content=b'')
        r = self._responses.pop(0)
        if isinstance(r, int):
            return types.SimpleNamespace(status_code=r, json=lambda: {'data': [{'id':'e1','name':'E1'}]}, content=b'')
        return r

class TestFetchSetsBackoff(unittest.TestCase):
    def test_batching_and_backoff(self):
        # Simulate: batch1 -> 429,429,200 ; batch2 -> 200
        cycling = CyclingSession([429, 429, 200, 200])
        fake = types.SimpleNamespace()
        fake.make_retry_session = lambda: cycling
        sys.modules['core.http_session'] = fake

        import importlib
        import core.twitch_emotes as te
        importlib.reload(te)
        from core.twitch_emotes import get_manager

        mgr = get_manager()
        mgr._backoff_base = 0.001
        mgr._emote_set_batch_size = 1

        # provide two emote set ids to force two batches
        mgr.fetch_emote_sets(['s1', 's2'])

        # After successful fetches, maps should contain emote id from responses
        self.assertIn('e1', mgr.id_map)

if __name__ == '__main__':
    unittest.main()
