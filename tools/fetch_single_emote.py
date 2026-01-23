import sys, time, os
sys.path.insert(0, '.')
from core.twitch_emotes import get_manager
from core.emotes import _get_global_emap

mgr = get_manager()
# blocking global prefetch
mgr.prefetch_global(background=False)
# small pause
time.sleep(0.1)
emap = _get_global_emap(mgr, broadcaster_id='853763018')
print('HAS_<3_in_map:', '<3' in (emap.map if emap else {}))
info = (emap.map.get('<3') if emap else None)
print('INFO:', info)
if info:
    try:
        uri = emap._ensure_data_uri('<3', info)
        print('FETCHED_URI_PREFIX:', (uri[:200] + '...') if uri else None)
    except Exception as e:
        print('ENSURE_ERROR', e)

# list recent cache files
cache_dir = None
try:
    cache_dir = getattr(mgr, 'cache_dir', None)
except Exception:
    cache_dir = None
if not cache_dir:
    cache_dir = os.path.join('resources', 'emotes')
files = []
try:
    files = [f for f in os.listdir(cache_dir) if os.path.isfile(os.path.join(cache_dir, f))]
except Exception:
    files = []
print('CACHE_FILES_COUNT:', len(files))
print('SAMPLE_FILES:', files[:20])
