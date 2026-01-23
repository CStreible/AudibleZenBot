"""
Install DejaVu fonts into the venv PyQt6 Qt6/lib/fonts directory.

Usage:
    python scripts/install_dejavu_fonts.py

The script will:
- Determine the active environment's site-packages/purelib directory
- Locate or create `PyQt6/Qt6/lib/fonts` under that path
- Download a small set of DejaVu TTF files from the official repo raw paths
- Save them to the fonts directory

This helps Qt6 QWebEngine find usable fonts on systems where Qt doesn't ship fonts.
"""

import os
import sys
import sysconfig
import urllib.request

FONT_FILES = [
    'DejaVuSans.ttf',
    'DejaVuSans-Bold.ttf',
    'DejaVuSansMono.ttf',
    'DejaVuSansMono-Bold.ttf',
    'DejaVuSerif.ttf',
    'DejaVuSerif-Bold.ttf',
]
BASE_URLS = [
    'https://github.com/dejavu-fonts/dejavu-fonts/raw/main/ttf',
    'https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf',
]


def main():
    try:
        purelib = sysconfig.get_paths().get('purelib')
    except Exception:
        purelib = None

    if not purelib:
        print('Could not determine site-packages/purelib path; aborting')
        return 2

    target_dir = os.path.join(purelib, 'PyQt6', 'Qt6', 'lib', 'fonts')
    try:
        os.makedirs(target_dir, exist_ok=True)
    except Exception as e:
        print(f'Failed to create target font directory {target_dir}: {e}')
        return 3

    print(f'Installing DejaVu fonts into: {target_dir}')

    success = 0
    for fname in FONT_FILES:
        dest = os.path.join(target_dir, fname)
        # try multiple base urls (main/master)
        downloaded = False
        for base in BASE_URLS:
            url = f"{base}/{fname}"
            try:
                # Skip download if already present
                if os.path.exists(dest) and os.path.getsize(dest) > 1000:
                    print(f'Exists: {fname} -> {dest}')
                    success += 1
                    downloaded = True
                    break
                print(f'Downloading {fname} from {url}...')
                urllib.request.urlretrieve(url, dest)
                if os.path.exists(dest) and os.path.getsize(dest) > 1000:
                    print(f'OK: {fname}')
                    success += 1
                    downloaded = True
                    break
                else:
                    # remove empty file if created
                    try:
                        if os.path.exists(dest) and os.path.getsize(dest) == 0:
                            os.remove(dest)
                    except Exception:
                        pass
            except Exception as e:
                # try next base url
                print(f'Attempt from {base} failed: {e}')
                continue
        if not downloaded:
            print(f'Failed to download {fname} from known locations')

    print(f'Downloaded {success}/{len(FONT_FILES)} fonts')
    if success == 0:
        print('No fonts downloaded from remote; attempting to copy common system fonts as a fallback')
        try:
            import shutil
            win_fonts = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts')
            candidates = ['arial.ttf', 'segoeui.ttf', 'segoeuib.ttf', 'Tahoma.ttf', 'calibri.ttf']
            copied = 0
            for name in candidates:
                src = os.path.join(win_fonts, name)
                if os.path.exists(src):
                    dst = os.path.join(target_dir, name)
                    try:
                        shutil.copy2(src, dst)
                        print(f'Copied system font {name} -> {dst}')
                        copied += 1
                    except Exception as e:
                        print(f'Failed to copy {src}: {e}')
            if copied > 0:
                print(f'Copied {copied} system fonts into {target_dir}')
                return 0
            else:
                print('No candidate system fonts found to copy; please install DejaVu manually into the fonts directory')
                return 4
        except Exception as e:
            print(f'Fallback copy failed: {e}')
            return 4

    print('Font installation complete.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
