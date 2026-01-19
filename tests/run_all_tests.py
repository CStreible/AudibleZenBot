import sys
import unittest
from pathlib import Path
import importlib.util


def discover_and_run():
    # limit discovery to the repository `tests/` directory
    base = Path(__file__).parent
    # ensure repo root is on sys.path so imports like `core` and `scripts` resolve
    repo_root = base.parent
    sys.path.insert(0, str(repo_root))
    import subprocess

    test_files = [p for p in sorted(base.rglob('test*.py')) if p.name != 'run_all_tests.py']
    overall_ok = True

    for path in test_files:
        # run each test file in a fresh subprocess to avoid shared-state issues
        rel = path.relative_to(base)
        parts = list(rel.with_suffix('').parts)
        modname = '.'.join(parts)
        cmd = [sys.executable, '-m', 'unittest', '-v', f'tests.{modname}']
        print(f"Running: {' '.join(cmd)}")
        try:
            proc = subprocess.run(cmd, cwd=str(repo_root))
            if proc.returncode != 0:
                overall_ok = False
        except Exception as e:
            print(f'ERROR running {modname}: {e}', file=sys.stderr)
            overall_ok = False

    return 0 if overall_ok else 1


if __name__ == '__main__':
    sys.exit(discover_and_run())
