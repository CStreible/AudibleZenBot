import sys, types, os
sys.path.insert(0, r'c:\Users\cstre\Dev\VS\AudibleZenBot')
# Create fake core.twitch_emotes to avoid network/imports
fake = types.ModuleType('core.twitch_emotes')
class FakeMgr:
    def __init__(self):
        # simulate id_map containing Kappa under id '25'
        self.id_map = {'25': {'name': 'Kappa'}}
    def get_emote_data_uri(self, emote_id, broadcaster_id=None):
        if str(emote_id) == '25':
            return 'data:image/png;base64,FAKE'
        return None
    def fetch_emote_sets(self, sets):
        return None
    def fetch_global_emotes(self):
        return None
    def fetch_channel_emotes(self, broadcaster_id):
        return None
fake.get_manager = lambda : FakeMgr()
sys.modules['core.twitch_emotes'] = fake
# Fake BTTV/FFZ manager
fake2 = types.ModuleType('core.bttv_ffz')
class FakeB:
    def ensure_channel(self, bid):
        return None
    name_map = {}
    def get_emote_data_uri_by_name(self, name, broadcaster_id=None):
        return None
fake2.get_manager = lambda : FakeB()
sys.modules['core.bttv_ffz'] = fake2

from core.emotes import render_message
# Run repro: Kappa with range-only tag
html_out, has_img = render_message('Kappa', '0-4', {'room-id':'853763018'})
print('has_img=', has_img)
print(html_out)

# Print debug log tail if exists
dbg = os.path.join(os.getcwd(), 'logs', 'emote_resolve_debug.log')
if os.path.exists(dbg):
    print('\n--- debug log ---')
    with open(dbg, 'r', encoding='utf-8', errors='replace') as f:
        for line in f.readlines()[-40:]:
            print(line.strip())
else:
    print('\nno debug log found')
