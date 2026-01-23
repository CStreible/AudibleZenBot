import importlib
import json
import time
from unittest.mock import Mock


def test_trovo_worker_autosaves_streamer_user_id(monkeypatch):
    mod = importlib.import_module('platform_connectors.trovo_connector')
    TrovoWorker = mod.TrovoWorker

    # Fake config that initially has no streamer_user_id
    class FakeCfg:
        def __init__(self):
            self.calls = []

        def get_platform_config(self, platform):
            return {}

        def set_platform_config(self, platform, key, val):
            self.calls.append((platform, key, val))

    fake_cfg = FakeCfg()

    # Prevent emit_chat from doing signal emits in test
    import platform_connectors.connector_utils as cu
    monkeypatch.setattr(cu, 'emit_chat', lambda *a, **k: None)

    worker = TrovoWorker(access_token='', channel='ChannelName', config=fake_cfg)

    # Craft a CHAT message where nick_name matches the channel name
    chat = {
        'type': 'CHAT',
        'data': {
            'chats': [
                {
                    'nick_name': 'ChannelName',
                    'uid': '999',
                    'message_id': 'm1',
                    'send_time': int(time.time()),
                    'content': 'hello'
                }
            ]
        }
    }

    worker.handle_message(json.dumps(chat))

    # Verify config saved streamer_user_id
    assert ('trovo', 'streamer_user_id', '999') in fake_cfg.calls


def test_connections_page_disable_persists_and_clears(monkeypatch):
    mod = importlib.import_module('ui.connections_page')
    PCW = mod.PlatformConnectionWidget

    # Fake self with attributes used by _on_disable_toggled
    fake = type('F', (), {})()
    fake.platform_id = 'myplat'
    fake.platform_name = 'MyPlat'
    fake.append_status_message = lambda v: None
    fake.disable_changed = Mock()
    fake.chat_manager = Mock()
    fake.streamer_display_name = type('L', (), {'setText': lambda self, v: None})()
    fake.bot_display_name = type('L', (), {'setText': lambda self, v: None})()
    fake.streamer_login_btn = type('B', (), {'setText': lambda self, v: None})()
    fake.bot_login_btn = type('B', (), {'setText': lambda self, v: None})()
    fake.status_label = type('S', (), {'setText': lambda self, v: None})()

    # Checkbox that reports checked=True
    fake.disable_checkbox = type('C', (), {'isChecked': lambda self: True})()

    # Provide a config on the instance to capture the initial disabled save
    class InstanceCfg:
        def __init__(self):
            self.calls = []

        def set_platform_config(self, platform, key, val):
            self.calls.append((platform, key, val))

    fake.config = InstanceCfg()

    # Monkeypatch module-level ConfigManager used to clear creds when disabled
    class ModuleCfg:
        last = None

        def __init__(self):
            ModuleCfg.last = self
            self.calls = []

        def set_platform_config(self, platform, key, val):
            self.calls.append((platform, key, val))

    monkeypatch.setattr(mod, 'ConfigManager', ModuleCfg)

    # Call the unbound method
    PCW._on_disable_toggled(fake, None)

    # Instance config should have saved the disabled flag
    assert ('myplat', 'disabled', True) in fake.config.calls

    # Module-level ConfigManager instance should have cleared streamer/bot keys
    inst = ModuleCfg.last
    assert inst is not None
    # Expect some keys cleared for streamer and bot
    assert any(call[1].startswith('streamer_') for call in inst.calls)
    assert any(call[1].startswith('bot_') for call in inst.calls)
