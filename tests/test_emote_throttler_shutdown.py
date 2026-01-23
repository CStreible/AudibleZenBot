import time
import unittest

from core.twitch_emotes import TwitchEmoteManager


class TestEmoteThrottlerShutdown(unittest.TestCase):
    def test_throttler_stops_on_request(self):
        m = TwitchEmoteManager(config=None)
        m._emote_set_batch_size = 5

        # simple no-op fetch to keep worker busy
        def noop_fetch(ids):
            return None

        m.fetch_emote_sets = noop_fetch

        # schedule work and give throttler time to start
        m.schedule_emote_set_fetch(['x', 'y', 'z'])
        time.sleep(0.15)

        # request stop and wait
        m.stop_emote_set_throttler(timeout=0.5)

        # throttler thread reference should be cleared
        self.assertTrue(m._throttler_thread is None or not getattr(m._throttler_thread, 'is_alive', lambda: False)())


if __name__ == '__main__':
    unittest.main()
