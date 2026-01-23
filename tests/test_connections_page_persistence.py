import importlib
from unittest.mock import Mock


class DummyBtn:
    def __init__(self, text_val):
        self._text = text_val

    def text(self):
        return self._text

    def setText(self, val):
        self._text = val


class DummyLabel:
    def __init__(self):
        self.text = ''

    def setText(self, val):
        self.text = val


def make_fake_self(platform_id='trovo', bot_logged_in=False):
    # Create an object with attributes used by onTrovoAccountAction
    fake = type('F', (), {})()
    fake.platform_id = platform_id
    fake.chat_manager = Mock()
    fake.streamer_login_btn = DummyBtn('Logout')
    fake.bot_login_btn = DummyBtn('Logout')
    fake.streamer_display_name = DummyLabel()
    fake.bot_display_name = DummyLabel()
    fake.status_label = DummyLabel()
    return fake


def test_connections_page_trovo_streamer_logout(monkeypatch):
    mod = importlib.import_module('ui.connections_page')
    PlatformConnectionWidget = mod.PlatformConnectionWidget

    fake_self = make_fake_self()

    # Fake ConfigManager to capture set_platform_config calls
    class FakeConfigManager:
        last = None
        def __init__(self, *a, **k):
            FakeConfigManager.last = self
            self.set_platform_config = Mock()

    import core.config as core_config
    monkeypatch.setattr(core_config, 'ConfigManager', FakeConfigManager)

    # Call the method as unbound function with our fake self
    # Call the method as unbound function on PlatformConnectionWidget
    PlatformConnectionWidget.onTrovoAccountAction(fake_self, 'streamer')

    inst = FakeConfigManager.last
    assert inst is not None
    inst.set_platform_config.assert_any_call('trovo', 'streamer_logged_in', False)
    inst.set_platform_config.assert_any_call('trovo', 'streamer_token', '')
    inst.set_platform_config.assert_any_call('trovo', 'streamer_refresh_token', '')


def test_connections_page_trovo_bot_logout(monkeypatch):
    mod = importlib.import_module('ui.connections_page')
    PlatformConnectionWidget = mod.PlatformConnectionWidget

    fake_self = make_fake_self()

    class FakeConfigManager:
        last = None
        def __init__(self, *a, **k):
            FakeConfigManager.last = self
            self.set_platform_config = Mock()

    import core.config as core_config
    monkeypatch.setattr(core_config, 'ConfigManager', FakeConfigManager)

    PlatformConnectionWidget.onTrovoAccountAction(fake_self, 'bot')

    inst = FakeConfigManager.last
    assert inst is not None
    inst.set_platform_config.assert_any_call('trovo', 'bot_logged_in', False)
    inst.set_platform_config.assert_any_call('trovo', 'bot_token', '')
    inst.set_platform_config.assert_any_call('trovo', 'bot_refresh_token', '')
