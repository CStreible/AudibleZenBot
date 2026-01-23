import time
import unittest

from core.emotes import render_message
from core.signals import signals as emote_signals


class TestEmotesSignals(unittest.TestCase):
    def test_render_emits_signal(self):
        received = []

        def cb(payload):
            received.append(payload)

        emote_signals.emotes_rendered_ext.connect(cb)

        html_out, has_img = render_message('hello world', None, metadata=None)
        # small sleep to allow async emit (if any)
        time.sleep(0.05)

        self.assertTrue(len(received) >= 1, f'expected render signal, got {received}')
        p = received[0]
        self.assertIn('timestamp', p)
        self.assertIn('has_img', p)
        self.assertIn('len_html', p)


if __name__ == '__main__':
    unittest.main()
