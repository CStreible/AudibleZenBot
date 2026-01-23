class QObject:
    pass

class QThread:
    def __init__(self):
        self.started = type('S', (), {'connect': lambda self, cb: None})()
        self.finished = type('S', (), {'connect': lambda self, cb: None})()

    def start(self):
        return None


def pyqtSlot(*args, **kwargs):
    def _d(f):
        return f
    return _d

class QTimer:
    @staticmethod
    def singleShot(ms, cb):
        try:
            # Best-effort: call callback after a short sleep in background
            def _delayed():
                try:
                    time.sleep(max(0, ms/1000.0))
                except Exception:
                    pass
                try:
                    cb()
                except Exception:
                    pass
            import threading
            threading.Thread(target=_delayed, daemon=True).start()
        except Exception:
            try:
                cb()
            except Exception:
                pass


class pyqtSignal:
    def __init__(self, *args, **kwargs):
        self._callbacks = []

    def connect(self, cb):
        try:
            self._callbacks.append(cb)
        except Exception:
            pass

    def emit(self, *args, **kwargs):
        for cb in list(self._callbacks):
            try:
                cb(*args, **kwargs)
            except Exception:
                pass
