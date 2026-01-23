"""Local copy of the `PyQt6` stub, renamed to `PyQt6_local` to avoid
shadowing a real PyQt6 installation during production runs.

This directory contains the same lightweight stubs but under a different
package name. Production runs will import the real `PyQt6` from
site-packages when available.
"""
import sys
from . import QtCore, QtWidgets

__all__ = ['QtCore', 'QtWidgets']
