"""Test-time Qt shims to improve headless WebEngine stability during CI.

This module ensures `QApplication` is constructed with a non-empty argv
when tests create it with an empty list (a Chromium requirement), and
enables verbose Chromium logging flags to stderr for diagnostics.
"""
import os
import sys

# Ensure Chromium gets useful flags in headless environments
os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS', '--no-sandbox --disable-gpu --headless --disable-software-rasterizer --enable-logging=stderr --v=1')
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

try:
    # Wrap QApplication to ensure it receives a non-empty argv
    from PyQt6.QtWidgets import QApplication as _QApp

    class _QAppWrapper(_QApp):
        def __init__(self, argv=None):
            if argv is None or len(argv) == 0:
                # Provide a fallback program name so Chromium's CommandLine
                # initialization does not abort with empty argv.
                argv = [sys.argv[0] or 'pytest']
            super().__init__(argv)

    # Monkeypatch QApplication in the PyQt6.QtWidgets module so tests that
    # call `QApplication([])` receive a wrapper that ensures a non-empty
    # argv (required by Chromium internals).
    try:
        import PyQt6.QtWidgets as _qtwidgets
        _qtwidgets.QApplication = _QAppWrapper
    except Exception:
        pass
except Exception:
    # If PyQt6 not available, nothing to do.
    pass
