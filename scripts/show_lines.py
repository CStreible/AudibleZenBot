import itertools
p='c:\\Users\\cstre\\Dev\\VS\\AudibleZenBot\\core\\twitch_emotes.py'
with open(p,'r',encoding='utf-8') as f:
    for i,l in enumerate(f, start=1):
        if 640<=i<=670:
            print(f"{i:4}: {l.rstrip()}\n  repr:{repr(l[:40])}")
