from core.config import ConfigManager
import requests, json, time

cm = ConfigManager()
ct = cm.get_platform_config('twitch') or {}
url = 'https://id.twitch.tv/oauth2/token'

data = None
refresh_key = None
if ct.get('refresh_token'):
    refresh_key = 'refresh_token'
elif ct.get('streamer_refresh_token'):
    refresh_key = 'streamer_refresh_token'
elif ct.get('bot_refresh_token'):
    refresh_key = 'bot_refresh_token'

if refresh_key:
    data = {
        'client_id': ct.get('client_id'),
        'client_secret': ct.get('client_secret'),
        'grant_type': 'refresh_token',
        'refresh_token': ct.get(refresh_key)
    }
elif ct.get('code'):
    data = {
        'client_id': ct.get('client_id'),
        'client_secret': ct.get('client_secret'),
        'grant_type': 'authorization_code',
        'code': ct.get('code'),
        'redirect_uri': ct.get('redirect_uri')
    }
else:
    open('tools/twitch_exchange_debug_verbose.json', 'w', encoding='utf-8').write(json.dumps({
        'ts': int(time.time()),
        'error': 'no refresh_token or code found in config',
        'platform_config_keys': list(ct.keys())
    }, indent=2))
    raise SystemExit('no refresh_token or code in twitch config')

# write debug (mask secret)
dbg = {'ts': int(time.time()), 'url': url, 'data': data.copy()}
if 'client_secret' in dbg['data']:
    dbg['data']['client_secret'] = '***'
open('tools/twitch_exchange_debug_verbose.json', 'w', encoding='utf-8').write(json.dumps(dbg, indent=2))

# perform request without retry adapter to see raw result
try:
    resp = requests.post(url, data=data, timeout=10)
    out = {'ts': int(time.time()), 'status_code': resp.status_code, 'text': resp.text, 'headers': dict(resp.headers)}
except Exception as e:
    out = {'ts': int(time.time()), 'error': str(e)}
open('tools/twitch_exchange_response_verbose.json', 'w', encoding='utf-8').write(json.dumps(out, indent=2))
print('Done')
