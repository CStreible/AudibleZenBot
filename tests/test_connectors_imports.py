import importlib
import inspect

MODULES = [
    'platform_connectors.twitch_connector',
    'platform_connectors.trovo_connector',
    'platform_connectors.dlive_connector',
    'platform_connectors.kick_connector_old_pusher',
    'platform_connectors.youtube_connector',
    'platform_connectors.twitter_connector',
]


def test_import_connectors():
    for m in MODULES:
        importlib.import_module(m)


def test_connectors_have_worker_classes():
    for m in MODULES:
        mod = importlib.import_module(m)
        classes = [
            obj
            for name, obj in vars(mod).items()
            if inspect.isclass(obj) and (name.endswith('Worker') or name.endswith('Connector'))
        ]
        assert classes, f"No Worker/Connector-like classes found in {m}"
