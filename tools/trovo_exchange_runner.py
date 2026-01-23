from core.config import ConfigManager
import requests, json, time

cm = ConfigManager()
trovo = cm.get_platform_config('trovo') or {}
url = 'https://open-api.trovo.live/openplatform/exchangetoken'
headers = {'Accept': 'application/json', 'client-id': trovo.get('client_id')}

# Use a known code if present in config, else a placeholder code
code = trovo.get('code') or '6ea05778baf9b07755d84541de8dced4'

data = {
    'client_id': trovo.get('client_id'),
    'client_secret': trovo.get('client_secret'),
    'grant_type': 'authorization_code',
    'code': code,
    'redirect_uri': 'https://mistilled-declan-unendable.ngrok-free.dev/callback'
}

# write outgoing debug (mask secret)
dbg = {'ts': int(time.time()), 'url': url, 'headers': headers, 'data': data.copy()}
if 'client_secret' in dbg['data']:
    dbg['data']['client_secret'] = '***'
open('tools/trovo_exchange_debug_retry.json', 'w', encoding='utf-8').write(json.dumps(dbg, indent=2))

# perform single POST (no retry adapter) to capture raw provider response
try:
    resp = requests.post(url, headers=headers, data=data, timeout=10)
    out = {'ts': int(time.time()), 'status_code': resp.status_code, 'text': resp.text, 'headers': dict(resp.headers)}
except Exception as e:
    out = {'ts': int(time.time()), 'error': str(e)}
open('tools/trovo_exchange_response_retry.json', 'w', encoding='utf-8').write(json.dumps(out, indent=2))
print('Done')
