"""Local PyQt6 stub proxy.

If a real PyQt6 is installed in site-packages, prefer loading that implementation
so the workspace-local stub doesn't shadow the real package. This file attempts
to load the installed `PyQt6/__init__.py` and re-exports its symbols. If that
fails, fall back to the minimal local stub behavior used for tests.
"""
import sys
import os
import importlib.util
import sysconfig
import types

from core.env import is_test

# Path to an installed PyQt6 package (if found)
installed_pkg_dir = None

def _load_installed_pyqt6():
	try:
		global installed_pkg_dir
		# Look through sys.path for a PyQt6 package that isn't this local folder
		local_dir = os.path.abspath(os.path.dirname(__file__))
		installed_pkg_dir = None
		for p in sys.path:
			try:
				candidate_dir = os.path.join(p, 'PyQt6')
				candidate = os.path.join(candidate_dir, '__init__.py')
				if not os.path.exists(candidate):
					continue
				if os.path.abspath(candidate_dir) == local_dir:
					continue
				installed_pkg_dir = candidate_dir
				break
			except Exception:
				continue
		if not installed_pkg_dir:
			return None
		spec = importlib.util.spec_from_file_location('_real_pyqt6', candidate)
		if not spec or not spec.loader:
			return None
		mod = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(mod)
		return mod
	except Exception:
		return None


def _register_submodule(module_obj, fullname):
	"""Create a real module object named `fullname` and copy attributes
	from `module_obj` into it, then register it in sys.modules and
	return the new module."""
	try:
		# Prefer registering the actual source module object so any subsequent
		# changes to the module attributes (during test-time edits) are visible
		# when importing submodules like `PyQt6.QtCore`.
		try:
			module_obj.__name__ = fullname
		except Exception:
			pass
		sys.modules[fullname] = module_obj
		return module_obj
	except Exception:
		return module_obj


# If explicitly running tests, prefer the local PyQt6_local stubs.
if is_test():
	try:
		from PyQt6_local import QtWidgets, QtCore  # type: ignore
		# Create real-named submodule objects so 'from PyQt6.QtCore import QThread' works
		globals()['QtWidgets'] = _register_submodule(QtWidgets, 'PyQt6.QtWidgets')
		globals()['QtCore'] = _register_submodule(QtCore, 'PyQt6.QtCore')
		# Also attempt to register webengine stubs if present
		try:
			from PyQt6_local import QtWebEngineWidgets, QtWebEngineCore  # type: ignore
			globals()['QtWebEngineWidgets'] = _register_submodule(QtWebEngineWidgets, 'PyQt6.QtWebEngineWidgets')
			globals()['QtWebEngineCore'] = _register_submodule(QtWebEngineCore, 'PyQt6.QtWebEngineCore')
		except Exception:
			pass
		try:
			from PyQt6_local import QtGui  # type: ignore
			globals()['QtGui'] = _register_submodule(QtGui, 'PyQt6.QtGui')
		except Exception:
			pass
	except Exception:
		# Fall back to the installed detection logic below
		_real = _load_installed_pyqt6()
		if _real:
			for _k, _v in _real.__dict__.items():
				if _k.startswith('__'):
					continue
				globals()[_k] = _v
			try:
				if installed_pkg_dir and os.path.isdir(installed_pkg_dir):
					__path__.insert(0, installed_pkg_dir)
			except Exception:
				pass
		else:
			from PyQt6_local import QtWidgets, QtCore  # type: ignore
			globals()['QtWidgets'] = _register_submodule(QtWidgets, 'PyQt6.QtWidgets')
			globals()['QtCore'] = _register_submodule(QtCore, 'PyQt6.QtCore')
			try:
				from PyQt6_local import QtWebEngineWidgets, QtWebEngineCore  # type: ignore
				globals()['QtWebEngineWidgets'] = _register_submodule(QtWebEngineWidgets, 'PyQt6.QtWebEngineWidgets')
				globals()['QtWebEngineCore'] = _register_submodule(QtWebEngineCore, 'PyQt6.QtWebEngineCore')
			except Exception:
				pass
			try:
				from PyQt6_local import QtGui  # type: ignore
				globals()['QtGui'] = _register_submodule(QtGui, 'PyQt6.QtGui')
			except Exception:
				pass
else:
	_real = _load_installed_pyqt6()
	if _real:
		# Re-export names from the installed package
		for _k, _v in _real.__dict__.items():
			if _k.startswith('__'):
				continue
			globals()[_k] = _v
		# Also extend this package __path__ so submodule imports (e.g., QtWebEngineWidgets)
		# can be resolved from the installed site-packages location.
		try:
			if installed_pkg_dir and os.path.isdir(installed_pkg_dir):
				__path__.insert(0, installed_pkg_dir)
		except Exception:
			pass
	else:
		# Minimal fallback stub used by tests
		from PyQt6_local import QtWidgets, QtCore  # type: ignore
		globals()['QtWidgets'] = _register_submodule(QtWidgets, 'PyQt6.QtWidgets')
		globals()['QtCore'] = _register_submodule(QtCore, 'PyQt6.QtCore')
		try:
			from PyQt6_local import QtWebEngineWidgets, QtWebEngineCore  # type: ignore
			globals()['QtWebEngineWidgets'] = _register_submodule(QtWebEngineWidgets, 'PyQt6.QtWebEngineWidgets')
			globals()['QtWebEngineCore'] = _register_submodule(QtWebEngineCore, 'PyQt6.QtWebEngineCore')
		except Exception:
			pass
		try:
			from PyQt6_local import QtGui  # type: ignore
			globals()['QtGui'] = _register_submodule(QtGui, 'PyQt6.QtGui')
		except Exception:
			pass
