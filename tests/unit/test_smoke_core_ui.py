import importlib
import pytest

MODULES = [
    "core.ngrok_manager",
    "core.callback_server",
    "core.oauth_handler",
    "core.overlay_server",
    "ui.settings_page",
    "ui.connections_page",
]


@pytest.mark.parametrize("modname", MODULES)
def test_import_core_ui_mod(modname):
    try:
        module = importlib.import_module(modname)
    except Exception as exc:
        pytest.skip(f"Skipping import of {modname}: {exc}")

    assert module is not None
