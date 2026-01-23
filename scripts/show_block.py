p='c:\\Users\\cstre\\Dev\\VS\\AudibleZenBot\\core\\twitch_emotes.py'
with open(p,'r',encoding='utf-8') as f:
    for i,l in enumerate(f, start=1):
        if 600<=i<=700:
            print(f"{i:4}:{len(l)-len(l.lstrip())} spaces |{l.rstrip()}|")
