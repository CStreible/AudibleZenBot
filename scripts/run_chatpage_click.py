"""Launch ChatPage, post a test message, simulate click, then delete it.

Run locally for a quick UI smoke test.
"""
import sys
import time

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from core.config import ConfigManager
from core.chat_manager import ChatManager
from core.overlay_server import OverlayServer
from ui.chat_page import ChatPage


def main():
    app = QApplication(sys.argv)

    config = ConfigManager()
    chat_manager = ChatManager(config)

    overlay = OverlayServer(port=5001)
    try:
        overlay.start()
    except Exception:
        pass

    page = ChatPage(chat_manager, config)
    page.overlay_server = overlay
    page.show()

    # Post a message shortly after startup so the page is ready
    def post_message():
        metadata = {
            'message_id': 'tw-1',
            'timestamp': time.time(),
            'badges': [],
            'color': '#22B2B2'
        }
        # Emit via signal so ChatPage receives it normally
        try:
            chat_manager.message_received.emit('twitch', 'Alice', 'Hello click test', metadata)
            print('Posted test message')
        except Exception as e:
            print('Emit failed:', e)

    # After message posted, simulate click and delete
    def simulate_click_and_delete():
        # Poll DOM for elements with data-message-id, retrying if necessary
        attempts = {'n': 0}

        list_ids_js = "Array.from(document.querySelectorAll('[data-message-id]')).map(e=>e.dataset.messageId)"

        def handle_ids(ids):
            try:
                print('DOM ids callback:', ids)
            except Exception:
                pass

            if not ids:
                attempts['n'] += 1
                if attempts['n'] < 40:
                    # Retry shortly
                    QTimer.singleShot(300, lambda: page.chat_display.page().runJavaScript(list_ids_js, handle_ids))
                else:
                    print('No message elements found after retries')
                return

            # Use the first id found (oldest)
            target_id = ids[0]
            print('Found message id:', target_id)

            # Dispatch a click on that element
            click_js = (
                f"(function(){{var el=document.querySelector('[data-message-id=\\\"{target_id}\\\"]');"
                "if(!el) return false; var ev=new MouseEvent('click',{bubbles:true,cancelable:true}); el.dispatchEvent(ev); return true; })()"
            )

            def after_click(res):
                print('click result:', res)
                # Read selectedMessageId and call deleteMessage
                def sel_cb(val):
                    print('window.selectedMessageId =', val)
                    if val:
                        try:
                            page.deleteMessage(val)
                            print('Called deleteMessage(', val, ')')
                        except Exception as e:
                            print('deleteMessage failed:', e)

                page.chat_display.page().runJavaScript('window.selectedMessageId', sel_cb)

            page.chat_display.page().runJavaScript(click_js, after_click)

        # Start polling
        page.chat_display.page().runJavaScript(list_ids_js, handle_ids)

    # Schedule the steps
    QTimer.singleShot(1500, post_message)
    QTimer.singleShot(5000, simulate_click_and_delete)
    QTimer.singleShot(8500, app.quit)

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
