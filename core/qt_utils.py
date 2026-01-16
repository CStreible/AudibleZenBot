from PyQt6.QtCore import QObject, pyqtSignal
import traceback


class MainThreadExecutor(QObject):
    """Schedule callables to run in the Qt main thread from any thread."""
    run = pyqtSignal(object, tuple, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.run.connect(self._call)

    def _call(self, func, args, kwargs):
        try:
            func(*args, **kwargs)
        except Exception:
            print("[MainThreadExecutor] Exception in scheduled function")
            traceback.print_exc()


_singleton = None


def get_main_thread_executor(parent=None):
    """Return a singleton MainThreadExecutor instance.

    The optional parent is ignored after the first creation.
    """
    global _singleton
    if _singleton is None:
        _singleton = MainThreadExecutor(parent)
    return _singleton
