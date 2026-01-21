class _Scripts:
    def insert(self, script):
        return None

try:
    from PyQt6_local.QtWidgets import _DummySignal
except Exception:
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


class _Page:
    def __init__(self):
        self._scripts = _Scripts()
        self._body_html = ''

    def scripts(self):
        return self._scripts

    def runJavaScript(self, js, callback=None):
        # Best-effort: if probing document.readyState, return 'complete'
        try:
            if isinstance(js, str) and 'document.readyState' in js:
                if callback:
                    try:
                        callback('complete')
                    except Exception:
                        pass
                return None
        except Exception:
            pass
        try:
            s = js if isinstance(js, str) else ''
            # Handle inserting HTML fragments via insertAdjacentHTML
            if 'insertAdjacentHTML' in s:
                try:
                    import re
                    m = re.search(r'`(.*)`', s, re.S)
                    if m:
                        frag = m.group(1)
                        try:
                            self._body_html += frag
                        except Exception:
                            pass
                except Exception:
                    pass
                if callback:
                    try:
                        callback(True)
                    except Exception:
                        pass
                return None

            # Handle reading innerHTML
            if "document.getElementById('chat-body').innerHTML" in s or 'document.getElementById("chat-body").innerHTML' in s:
                # Clear innerHTML
                if "= ''" in s or "= \"\"" in s:
                    self._body_html = ''
                    if callback:
                        try:
                            callback(True)
                        except Exception:
                            pass
                    return None
                # Return current innerHTML
                if callback:
                    try:
                        callback(self._body_html)
                    except Exception:
                        pass
                return None
        except Exception:
            pass
        except Exception:
            pass
        if callback:
            try:
                callback(None)
            except Exception:
                pass
        return None


class QWebEngineView:
    def __init__(self, *args, **kwargs):
        self._page = _Page()
        self.customContextMenuRequested = _DummySignal()

    def setHtml(self, html, baseUrl=None):
        self._html = html

    def page(self):
        return self._page
    def setContextMenuPolicy(self, policy):
        self._context_menu_policy = policy
    def setSizePolicy(self, w, h):
        self._size_policy = (w, h)
    def setMinimumHeight(self, h):
        self._min_height = h
    def showContextMenu(self, *args, **kwargs):
        return None
