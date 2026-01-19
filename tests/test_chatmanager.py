import unittest
import time
from core.chat_manager import ChatManager


class ChatManagerTests(unittest.TestCase):

    def setUp(self):
        self.cm = ChatManager(config=None)
        self.received = []
        self.cm.message_received.connect(self._handler)

    def _handler(self, platform, username, message, metadata):
        self.received.append((platform, username, message, metadata))

    def test_dedup_by_message_id(self):
        # Two messages with same message_id should be deduplicated
        self.cm.onMessageReceivedWithMetadata('test', 'UserA', 'Hello', {'message_id': 'mid-123'})
        self.cm.onMessageReceivedWithMetadata('test', 'UserA', 'Hello', {'message_id': 'mid-123'})
        # Allow tiny time for signals
        time.sleep(0.01)
        self.assertEqual(len(self.received), 1)

    def test_canonicalization_username_format(self):
        # Different username formatting should canonicalize and dedupe
        self.cm.onMessageReceivedWithMetadata('test', 'User_Name', 'Hey', {})
        self.cm.onMessageReceivedWithMetadata('test', 'user name', 'Hey', {})
        time.sleep(0.01)
        self.assertEqual(len(self.received), 1)

    def test_similar_message_different_platforms(self):
        # Same message on different platforms should both be emitted
        self.cm.onMessageReceivedWithMetadata('p1', 'Bob', 'Hi', {})
        self.cm.onMessageReceivedWithMetadata('p2', 'Bob', 'Hi', {})
        time.sleep(0.01)
        self.assertEqual(len(self.received), 2)

    def test_deletion_handling(self):
        # onMessageDeleted should emit message_deleted signal
        deleted = []
        self.cm.message_deleted.connect(lambda platform, mid: deleted.append((platform, mid)))
        self.cm.onMessageDeleted('pdel', 'del-1')
        time.sleep(0.01)
        self.assertEqual(deleted, [('pdel', 'del-1')])

    def test_rapid_burst_duplicates(self):
        # Rapid repeated identical messages should be deduplicated
        for _ in range(10):
            self.cm.onMessageReceivedWithMetadata('rb', 'Spammer', 'Spam!', {})
        time.sleep(0.02)
        # only one should be emitted
        self.assertEqual(len([r for r in self.received if r[0] == 'rb']), 1)

    def test_sendMessageAsBot_echo(self):
        # Create a fake bot connector that reports connected and returns True on send
        class FakeBot:
            def __init__(self):
                self.connected = True
            def send_message(self, message):
                return True

        fake = FakeBot()
        self.cm.bot_connectors['kick'] = fake
        # Clear received and send message as bot
        self.received.clear()
        ok = self.cm.sendMessageAsBot('kick', 'EchoTest', allow_fallback=True)
        time.sleep(0.02)
        self.assertTrue(ok)
        # Non-Twitch platforms are echoed; check we received an echoed message
        found = [r for r in self.received if r[0] == 'kick' and r[2] == 'EchoTest']
        self.assertTrue(len(found) >= 1)


if __name__ == '__main__':
    unittest.main()
