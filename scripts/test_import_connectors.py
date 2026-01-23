modules = ['platform_connectors.twitch_connector','platform_connectors.trovo_connector','platform_connectors.kick_connector','platform_connectors.dlive_connector','platform_connectors.youtube_connector']
import importlib, traceback
for m in modules:
    try:
        mod = importlib.import_module(m)
        print(m, 'imported ->', getattr(mod, '__file__', None))
    except Exception as e:
        print(m, 'FAILED:', type(e), e)
        traceback.print_exc()
