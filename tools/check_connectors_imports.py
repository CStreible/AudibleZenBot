import importlib, sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
mods=['platform_connectors.twitch_connector','platform_connectors.kick_connector','platform_connectors.trovo_connector','platform_connectors.dlive_connector','platform_connectors.youtube_connector','platform_connectors.kick_connector_old_pusher','platform_connectors.twitter_connector']
for m in mods:
    try:
        importlib.import_module(m)
        print(m+' OK')
    except Exception as e:
        print(m+' ERR '+str(e))
