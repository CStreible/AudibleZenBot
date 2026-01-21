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
            def _delayed():
                try:
                    import time
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


# Minimal Qt namespace placeholder (flags/constants not needed for tests)
class Qt:
    AlignLeft = 0
    AlignRight = 1
    AlignCenter = 2
    class ScrollBarPolicy:
        ScrollBarAsNeeded = 0
        ScrollBarAlwaysOff = 1
    class ContextMenuPolicy:
        NoContextMenu = 0
        DefaultContextMenu = 1
        CustomContextMenu = 2


class QUrl:
    def __init__(self, url_str=''):
        self._url = url_str

    def toString(self):
        return str(self._url)
import threading


class QEventLoop:
    def __init__(self):
        self._running = False
        self._cond = threading.Condition()

    def exec(self):
        self._running = True
        with self._cond:
            while self._running:
                self._cond.wait(timeout=0.1)

    def quit(self):
        with self._cond:
            self._running = False
            try:
                self._cond.notify_all()
            except Exception:
                pass
