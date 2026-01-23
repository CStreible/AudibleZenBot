p='c:\\Users\\cstre\\Dev\\VS\\AudibleZenBot\\core\\twitch_emotes.py'
with open(p,'r',encoding='utf-8') as f:
    for i,l in enumerate(f, start=1):
        if 380<=i<=404:
            print(f"{i:4}:{repr(l[:60])}")
