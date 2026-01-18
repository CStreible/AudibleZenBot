"""
Simple diagnostic script to dump connector and ngrok states.
Run from repository root using the virtualenv Python:

python -m scripts.diag_connectors

"""
import json
import time

from core.config import ConfigManager
from core.ngrok_manager import NgrokManager
from core.chat_manager import ChatManager


def main():
    cfg = ConfigManager()
    ng = NgrokManager(cfg)
    cm = ChatManager(cfg)
    # Ensure ChatManager can inspect ngrok
    cm.ngrok_manager = ng

    # Small delay to allow any background initialization
    time.sleep(0.2)

    snap = cm.dump_connector_states()
    print(json.dumps(snap, indent=2, default=str))


if __name__ == '__main__':
    main()
