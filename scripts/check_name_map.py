from core.twitch_emotes import get_manager
m = get_manager()
print('Forcing synchronous global prefetch...')
m.prefetch_global(background=False)
print('Kappa in name_map:', 'Kappa' in m.name_map, '->', m.name_map.get('Kappa'))
print('sample name_map keys:', list(m.name_map.keys())[:20])
