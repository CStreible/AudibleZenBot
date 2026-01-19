import unittest
import time
import re
import sys
import sysconfig
import os

# Ensure venv/site-packages appears before workspace to avoid local PyQt6/requests shadowing
try:
    purelib = sysconfig.get_paths().get('purelib')
    if purelib and purelib not in sys.path:
        sys.path.insert(0, purelib)
except Exception:
    pass

from PyQt6.QtWidgets import QApplication

from core.chat_manager import ChatManager

# Temporarily remove workspace root from sys.path so installed PyQt6 is imported
_orig_sys_path = list(sys.path)
_cwd = os.path.abspath(os.getcwd())
try:
    # Temporarily remove workspace root so we import installed PyQt6
    for p in list(sys.path):
        try:
            if not p or os.path.abspath(p) == _cwd:
                sys.path.remove(p)
        except Exception:
            pass
    try:
        import PyQt6 as _pyqt6_dummy
    except Exception:
        # ignore - best-effort import to bind installed package
        pass
finally:
    # Restore sys.path so local packages (ui, core) can be imported
    sys.path[:] = _orig_sys_path


# Detect if PyQt6 + QWebEngine are importable in this environment; if not, skip integration tests.
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView  # noqa: F401
    HAS_PYQT_WEBENGINE = True
except Exception:
    HAS_PYQT_WEBENGINE = False


def get_inner_html(page, timeout=2.0):
    """Helper to synchronously fetch innerHTML of chat-body from QWebEnginePage."""
    result = {'html': None}

    def cb(r):
        result['html'] = r

    page.runJavaScript("document.getElementById('chat-body') ? document.getElementById('chat-body').innerHTML : ''", cb)

    # wait for callback
    waited = 0.0
    interval = 0.05
    while result['html'] is None and waited < timeout:
        QApplication.processEvents()
        time.sleep(interval)
        waited += interval

    return result['html'] or ''


@unittest.skipIf(not HAS_PYQT_WEBENGINE, "PyQt6 WebEngine not available in this environment")
class ChatPageIntegrationTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Ensure a QApplication exists
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.cm = ChatManager(config=None)
        # Import ChatPage here to avoid module-level PyQt imports when unavailable
        from ui.chat_page import ChatPage
        self.page = ChatPage(self.cm, config=None)

    def test_message_renders_in_chat_body(self):
        # Send a message and verify it appears in chat-body HTML
        self.cm.onMessageReceivedWithMetadata('int', 'Alice', 'HelloIntegration', {})
        # allow JS to execute
        time.sleep(0.2)
        html = get_inner_html(self.page.chat_display.page(), timeout=2.0)
        self.assertIn('HelloIntegration', html)
        self.assertIn('data-message-id="msg_', html)

    def test_platform_deletion_removes_message(self):
        # Send message with platform message_id and ensure deletion removes mapping
        self.cm.onMessageReceivedWithMetadata('pint', 'Bob', 'ToDelete', {'message_id': 'del-42'})
        time.sleep(0.2)
        key = 'pint:del-42'
        # Mapping should exist
        self.assertIn(key, self.page.platform_message_id_map)
        # Trigger platform deletion
        self.cm.onMessageDeleted('pint', 'del-42')
        time.sleep(0.3)
        # Mapping should be removed and message_data should not contain mapped id
        self.assertNotIn(key, self.page.platform_message_id_map)

    def test_multiple_messages_count(self):
        # Post multiple messages and verify count in HTML
        for i in range(3):
            self.cm.onMessageReceivedWithMetadata('mcount', f'User{i}', f'Msg{i}', {})
        time.sleep(0.3)
        html = get_inner_html(self.page.chat_display.page(), timeout=2.0)
        count = len(re.findall(r'data-message-id="msg_', html))
        self.assertGreaterEqual(count, 3)


if __name__ == '__main__':
    unittest.main()
