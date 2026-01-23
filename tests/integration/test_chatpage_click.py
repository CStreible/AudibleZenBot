import os
import time
import pytest

try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QEventLoop, QTimer
    HAS_PYQT = True
except Exception:
    HAS_PYQT = False

from core.config import ConfigManager
from core.chat_manager import ChatManager
from ui.chat_page import ChatPage


pytestmark = pytest.mark.integration


def _run_js_and_wait(page, js_expr, timeout_ms=5000, poll_ms=250):
    end = time.time() + (timeout_ms / 1000.0)
    while time.time() < end:
        loop = QEventLoop()
        result_container = {'val': None}

        def cb(res):
            result_container['val'] = res
            QTimer.singleShot(0, loop.quit)

        try:
            page.chat_display.page().runJavaScript(js_expr, cb)
        except Exception:
            # If runJavaScript is not available, bail out
            return None

        # Ensure the event loop runs for up to poll_ms waiting for the callback
        QTimer.singleShot(poll_ms, loop.quit)
        loop.exec()

        val = result_container['val']
        if val:
            return val
        # otherwise loop and retry
    return None


@pytest.mark.skipif(not HAS_PYQT, reason="PyQt6 not available")
@pytest.mark.skipif(os.environ.get('AZB_ENABLE_WEBENGINE_TESTS') != '1', reason="Enable WebEngine tests with AZB_ENABLE_WEBENGINE_TESTS=1")
def test_chatpage_click_flow():
    """Integration test: render ChatPage, post message, simulate click, verify deletion."""
    app = QApplication.instance() or QApplication([])

    config = ConfigManager()
    chat_manager = ChatManager(config)

    page = ChatPage(chat_manager, config)
    page.overlay_server = None
    page.show()

    # Post a test message via the ChatManager signal
    metadata = {
        'message_id': 'test-1',
        'timestamp': time.time(),
        'badges': [],
        'color': '#22B2B2'
    }
    chat_manager.message_received.emit('twitch', 'pytest_user', 'Hello pytest click test', metadata)

    # Wait for the DOM to contain message elements
    js_list_ids = "Array.from(document.querySelectorAll('[data-message-id]')).map(e=>e.dataset.messageId)"
    ids = _run_js_and_wait(page, js_list_ids, timeout_ms=10000, poll_ms=300)
    assert ids and isinstance(ids, (list, tuple)) and len(ids) > 0, f"No message ids found in DOM: {ids}"

    target = ids[0]

    # Dispatch a click on the element
    click_js = f"(function(){{var el=document.querySelector('[data-message-id=\\\"{target}\\\"]'); if(!el) return false; el.dispatchEvent(new MouseEvent('click',{{bubbles:true,cancelable:true}})); return true; }})()"
    click_res = _run_js_and_wait(page, click_js, timeout_ms=2000, poll_ms=100)
    assert click_res is True or click_res == 'true' or click_res == 1

    # Verify the page's selectedMessageId was set
    sel = _run_js_and_wait(page, 'window.selectedMessageId', timeout_ms=2000, poll_ms=100)
    assert sel == target

    # Call deleteMessage and verify internal state cleanup
    page.deleteMessage(sel)
    assert sel not in page.message_data

    page.close()
