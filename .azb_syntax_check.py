import compileall
import os
import sys

exclude_dirs = {'.venv', 'build', '__pycache__'}
root = '.'
errors = []

for dp, dirs, files in os.walk(root):
    # skip excluded dirs anywhere in path
    parts = set(dp.replace('\\','/').split('/'))
    if parts & exclude_dirs:
        continue
    for f in files:
        if not f.endswith('.py'):
            continue
        path = os.path.join(dp, f)
        try:
            ok = compileall.compile_file(path, quiet=1)
            if not ok:
                errors.append(path)
        except Exception as e:
            errors.append(f"{path}: {e}")

if errors:
    print('Syntax check failures:')
    for e in errors:
        print(' -', e)
    sys.exit(1)
else:
    print('Syntax check passed (no syntax errors found)')
    sys.exit(0)
