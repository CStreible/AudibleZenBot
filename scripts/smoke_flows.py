import time
import os
import requests

from scripts import headless_runner as hr


def ensure_overlay():
    try:
        hr.overlay_server.start()
    except Exception:
        pass


def post_connector_message(platform, username, message, message_id=None):
    md = {}
    if message_id:
        md['message_id'] = message_id
    print(f"Posting message via ChatManager: {platform},{username},{message},{md}")
    try:
        hr.chat_manager.onMessageReceivedWithMetadata(platform, username, message, md)
    except Exception as e:
        print('Error posting message to ChatManager:', e)


def delete_connector_message(platform, message_id):
    print(f"Triggering deletion via ChatManager: {platform},{message_id}")
    try:
        hr.chat_manager.onMessageDeleted(platform, message_id)
    except Exception as e:
        print('Error triggering deletion on ChatManager:', e)


def fetch_overlay_messages():
    try:
        r = requests.get('http://127.0.0.1:5000/overlay/messages', timeout=2)
        return r.json()
    except Exception as e:
        print('Error fetching overlay messages:', e)
        return None


def tail_log(path, last_n=20):
    if not os.path.exists(path):
        return ''
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
    return ''.join(lines[-last_n:])


def run():
    ensure_overlay()
    # Post a few connector messages
    post_connector_message('twitch', 'Alice', 'Hello from Alice', 'tw-1')
    time.sleep(0.2)
    post_connector_message('kick', 'Bob', 'Hi from Bob', 'kick-1')
    time.sleep(0.2)
    # Also add an overlay-only message
    try:
        hr.overlay_server.add_message('overlay', 'OverlayUser', 'Overlay-only message', 'ov-1')
    except Exception as e:
        print('Error adding overlay message:', e)

    time.sleep(0.5)
    print('Overlay messages after posting:')
    print(fetch_overlay_messages())

    # Check chatmanager emit log
    print('\nRecent chatmanager emits:')
    print(tail_log(os.path.join(os.getcwd(), 'logs', 'chatmanager_emitted.log')))

    # Trigger deletion for twitch message
    delete_connector_message('twitch', 'tw-1')
    # Remove overlay message
    try:
        hr.overlay_server.remove_message('ov-1')
    except Exception as e:
        print('Error removing overlay message:', e)

    time.sleep(0.3)
    print('Overlay messages after deletion:')
    print(fetch_overlay_messages())


if __name__ == '__main__':
    run()
