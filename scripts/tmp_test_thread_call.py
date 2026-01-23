from core.twitch_emotes import TwitchEmoteManager
import threading

mgr = TwitchEmoteManager(config=None)

calls = []

def fake_fetch(batch):
    print('FAKE_FETCH called', threading.current_thread().name, 'batch=', batch)
    calls.append(list(batch))

mgr.fetch_emote_sets = fake_fetch

th = threading.Thread(target=lambda: mgr.fetch_emote_sets(['a','b']), daemon=True)
th.start()
th.join(1)
print('calls after thread:', calls)
