import ast
import pathlib
import sys
import traceback
import os

errs = 0

for p in pathlib.Path('.').rglob('*.py'):
    sp = str(p)
    # Exclude virtualenv folders by path components
    parts = [str(x).lower() for x in p.parts]
    if any(x in parts for x in ('.venv', 'venv', '.venv-1')):
        continue
    try:
        with open(p, 'r', encoding='utf-8') as fh:
            ast.parse(fh.read(), filename=sp)
        print('OK', sp)
    except Exception:
        print('ERR', sp)
        traceback.print_exc()
        errs = 1

sys.exit(errs)
