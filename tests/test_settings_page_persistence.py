import importlib
from unittest.mock import Mock


def make_fake_self():
    fake = type('F', (), {})()
    fake.config = Mock()
    # cred_rows maps platform -> (id_input, secret_input)
    class FakeInput:
        def __init__(self, text):
            self._text = text

        def text(self):
            return self._text

        def setText(self, v):
            self._text = v

    fake.cred_rows = {'youtube': (FakeInput('cid123'), FakeInput('csec456'))}
    # sender() should return an object with property 'platform'
    class Sender:
        def __init__(self, platform):
            self._platform = platform

        def property(self, name):
            if name == 'platform':
                return self._platform
            return None

    fake._sender = Sender('youtube')
    fake.sender = lambda: fake._sender
    return fake


def test_settings_save_calls_set_platform_config(monkeypatch):
    mod = importlib.import_module('ui.settings_page')
    SettingsPage = mod.SettingsPage

    fake = make_fake_self()

    class FakeConfigManager:
        last = None
        def __init__(self, *a, **k):
            FakeConfigManager.last = self
            self.set_platform_config = Mock()

    import core.config as core_config
    monkeypatch.setattr(core_config, 'ConfigManager', FakeConfigManager)

    # Prevent QMessageBox from requiring a real QWidget parent
    import ui.settings_page as settings_page
    monkeypatch.setattr(settings_page.QMessageBox, 'information', lambda *a, **k: None)
    monkeypatch.setattr(settings_page.QMessageBox, 'warning', lambda *a, **k: None)

    # Call the protected save method as unbound function
    SettingsPage._save_platform_credentials(fake)

    # make_fake_self provided a Mock config on the fake; assert it was used
    inst = fake.config
    inst.set_platform_config.assert_any_call('youtube', 'client_id', 'cid123')
    inst.set_platform_config.assert_any_call('youtube', 'client_secret', 'csec456')
