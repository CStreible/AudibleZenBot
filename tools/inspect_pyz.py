import zipfile, sys
p='build/AudibleZenBot/PYZ-00.pyz'
try:
    with zipfile.ZipFile(p) as z:
        names=[n for n in z.namelist() if 'connections_page' in n.lower()]
        for n in names:
            print(n)
        print('--- total entries:', len(z.namelist()))
except Exception as e:
    print('ERROR', e)
    sys.exit(1)
