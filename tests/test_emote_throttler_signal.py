import time
import unittest

from core.twitch_emotes import TwitchEmoteManager
from core.signals import signals as emote_signals


class TestEmoteThrottlerSignal(unittest.TestCase):
    def test_throttler_emits_signal_payload(self):
        m = TwitchEmoteManager(config=None)

        received = []

        def cb(payload):
            try:
                # copy minimal fields for assertion
                received.append(payload)
            except Exception:
                pass

        # Connect stub callback
        emote_signals.emote_set_batch_processed_ext.connect(cb)

        # Ensure fetch does nothing (no network) so worker emits payload quickly
        def noop_fetch(ids):
            return None

        m.fetch_emote_sets = noop_fetch

        # Schedule a batch and wait for the worker to process
        m.schedule_emote_set_fetch(['s1', 's2'])
        time.sleep(0.2)
        m.stop_emote_set_throttler()

        self.assertTrue(len(received) >= 1, f'expected signal payloads, got {received}')
        payload = received[0]
        self.assertIn('status', payload)
        self.assertIn('emote_set_count', payload)
        self.assertIn('attempts', payload)


if __name__ == '__main__':
    unittest.main()
