"""Lightweight Qt compatibility layer for connectors.

When PyQt6 is available we re-export the real types. When it's not
available we provide minimal fallbacks so connectors and tests can
import modules and run in headless environments without raising at
import time.
"""
try:
    from PyQt6.QtCore import QObject, QThread, pyqtSignal  # type: ignore
    HAS_QT = True
except Exception:
    HAS_QT = False
    import threading

    class QObject:
        def __init__(self, *args, **kwargs):
            # Minimal noop base class to satisfy super().__init__() calls
            return None

    class _DummySignal:
        def __init__(self):
            self._slots = []

        def connect(self, fn):
            try:
                self._slots.append(fn)
            except Exception:
                pass

        def emit(self, *args, **kwargs):
            for s in list(self._slots):
                try:
                    s(*args, **kwargs)
                except Exception:
                    pass

    class _SignalDescriptor:
        def __init__(self, *args, **kwargs):
            self._name = None

        def __set_name__(self, owner, name):
            self._name = name

        def __get__(self, instance, owner=None):
            if instance is None:
                return self
            signals = getattr(instance, '__signals__', None)
            if signals is None:
                signals = {}
                setattr(instance, '__signals__', signals)
            if self._name not in signals:
                signals[self._name] = _DummySignal()
            return signals[self._name]

    def pyqtSignal(*args, **kwargs):
        # Ignore signature args - return a descriptor that yields a per-instance
        # _DummySignal object.
        return _SignalDescriptor()

    class QThread(threading.Thread):
        def __init__(self, *args, **kwargs):
            # Accept same initialization pattern as QThread but back to Thread
            super().__init__(daemon=kwargs.pop('daemon', True))
            self._running = False

        def run(self):
            # threading.Thread.run will call the target; keep behavior
            try:
                super().run()
            except Exception:
                pass

        def start(self):
            self._running = True
            try:
                super().start()
            except Exception:
                pass

        def wait(self, timeout_ms=None):
            try:
                if timeout_ms is None:
                    super().join()
                else:
                    super().join(timeout_ms / 1000.0)
            except Exception:
                pass

        def quit(self):
            # No-op for compatibility
            self._running = False
