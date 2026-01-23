p='c:\\Users\\cstre\\Dev\\VS\\AudibleZenBot\\core\\twitch_emotes.py'
from pathlib import Path
text=Path(p).read_text(encoding='utf-8').splitlines()
for i in range(620, 666):
    l=text[i-1]
    print(f"{i}: {len(l)-len(l.lstrip())} spaces |{l.rstrip()}|")
