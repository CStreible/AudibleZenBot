import importlib

MODULES = [
    'core.ngrok_manager',
    'core.callback_server',
    'core.oauth_handler',
    'core.overlay_server',
]


def test_core_modules_importable():
    for m in MODULES:
        mod = importlib.import_module(m)
        importlib.reload(mod)
        assert hasattr(mod, '__name__')
        # Ensure module exposes at least one public symbol
        public = [n for n in dir(mod) if not n.startswith('_')]
        assert len(public) > 0
