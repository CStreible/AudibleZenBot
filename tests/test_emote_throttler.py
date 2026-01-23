import time
import unittest

from core.twitch_emotes import TwitchEmoteManager, PrefetchError


class TestEmoteThrottler(unittest.TestCase):
    def test_batch_combine_and_retry(self):
        m = TwitchEmoteManager(config=None)
        m._emote_set_batch_size = 10

        calls = []
        state = {'calls': 0}

        def fake_fetch(emote_set_ids):
            state['calls'] += 1
            calls.append(list(emote_set_ids))
            if state['calls'] == 1:
                raise PrefetchError('network', 'simulated transient')
            return None

        # Patch instance method
        m.fetch_emote_sets = fake_fetch

        # enqueue two batches which should be combined by throttler
        m.schedule_emote_set_fetch(['a', 'b', 'c'])
        m.schedule_emote_set_fetch(['d', 'e'])

        # allow worker to run and retry
        time.sleep(0.4)

        # stop throttler
        m.stop_emote_set_throttler()

        # ensure fetch was invoked and retry occurred
        self.assertGreaterEqual(state['calls'], 2, 'expected at least one retry attempt')

        # combined call should contain all enqueued ids in at least one invocation
        combined_seen = any(set(['a', 'b', 'c', 'd', 'e']).issubset(set(c)) for c in calls)
        self.assertTrue(combined_seen, f'expected combined batch in calls; got {calls}')


if __name__ == '__main__':
    unittest.main()
import time
import unittest
import sys
import types

# Provide a lightweight stub for core.http_session to avoid requiring 'requests' in tests
fake_http = types.SimpleNamespace()
def make_retry_session():
    class S:
        def get(self, url, headers=None, params=None, timeout=None):
            class R:
                status_code = 200
                def json(self):
                    return {'data': []}
                content = b''
            return R()
    return S()
fake_http.make_retry_session = make_retry_session
sys.modules['core.http_session'] = fake_http

from core.twitch_emotes import TwitchEmoteManager


class TestEmoteThrottler(unittest.TestCase):
    def test_schedule_and_process_batches(self):
        mgr = TwitchEmoteManager(config=None)
        calls = []

        # Monkeypatch fetch_emote_sets to record batches processed
        def fake_fetch(batch):
            calls.append(list(batch))

        mgr.fetch_emote_sets = fake_fetch

        # Ensure throttler is not running yet
        assert mgr._throttler_thread is None or not mgr._throttler_thread.is_alive()

        # Schedule multiple emote_set ids
        scheduled = mgr.schedule_emote_set_fetch(['a', 'b', 'c'])
        self.assertTrue(scheduled)

        # Wait for background worker to process queue
        timeout = time.time() + 2.0
        while time.time() < timeout and not calls:
            time.sleep(0.02)

        # Stop the throttler
        mgr.stop_emote_set_throttler()

        # Assert that our fake_fetch was called with the expected batch
        self.assertTrue(len(calls) >= 1)
        # Flatten and compare contents
        flattened = [s for batch in calls for s in batch]
        for expected in ('a', 'b', 'c'):
            self.assertIn(expected, flattened)


if __name__ == '__main__':
    unittest.main()
