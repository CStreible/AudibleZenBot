import unittest
import time
from unittest.mock import MagicMock, patch

from core.twitch_emotes import TwitchEmoteManager, PrefetchError


class TestEmoteThrottlerFinish(unittest.TestCase):
    def test_throttler_retries_and_shutdown(self):
        mgr = TwitchEmoteManager(config={})

        # Patch fetch_emote_sets to fail twice with rate_limited then succeed
        calls = {'count': 0}

        def side_effect(batch):
            calls['count'] += 1
            if calls['count'] < 3:
                raise PrefetchError('rate_limited', 'HTTP 429')
            return None

        mgr.fetch_emote_sets = MagicMock(side_effect=side_effect)

        # Speed up sleeps by patching time.sleep to no-op
        with patch('time.sleep', lambda s: None):
            # Schedule a batch and start throttler
            mgr.schedule_emote_set_fetch(['1', '2', '3'])
            mgr.start_emote_set_throttler()

            # Wait a short time for worker to process retries
            timeout = time.time() + 2.0
            while time.time() < timeout and calls['count'] < 3:
                time.sleep(0.01)

            # Stop worker
            mgr.stop_emote_set_throttler()

        # Ensure fetch_emote_sets was called at least 3 times (2 failures + 1 success)
        assert calls['count'] >= 3


if __name__ == '__main__':
    unittest.main()
