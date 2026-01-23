class QApplication:
    def __init__(self, *args, **kwargs):
        pass

    def exec(self):
        return 0

    def aboutToQuit(self):
        class S:
            def connect(self, cb):
                return None
        return S()


class QWidget:
    def __init__(self, parent=None):
        # Minimal init to accept parent and avoid calling object.__init__ with args
        self._parent = parent


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


class QVBoxLayout:
    def __init__(self, *args, **kwargs):
        self._items = []

    def setContentsMargins(self, l, t, r, b):
        return None

    def setSpacing(self, s):
        return None

    def addWidget(self, w, stretch=None, alignment=None):
        self._items.append(('widget', w, stretch, alignment))

    def addLayout(self, layout):
        self._items.append(('layout', layout))

    def addStretch(self, n=0):
        return None

    def setSizeConstraint(self, c):
        return None


class QLabel:
    def __init__(self, *args, **kwargs):
        pass
    def setStyleSheet(self, _):
        pass
    def setMaximumHeight(self, h):
        pass


class QGroupBox:
    def __init__(self, *args, **kwargs):
        pass
    def setMaximumHeight(self, h):
        pass
    def setStyleSheet(self, s):
        pass
    def setLayout(self, layout):
        self._layout = layout


class QHBoxLayout:
    def __init__(self, *args, **kwargs):
        self._items = []

    def setSpacing(self, s):
        pass

    def setContentsMargins(self, l, t, r, b):
        pass

    def addWidget(self, w, stretch=None, alignment=None):
        self._items.append(('widget', w, stretch, alignment))

    def addStretch(self, n=0):
        return None


class QCheckBox:
    def __init__(self, *args, **kwargs):
        self.stateChanged = _DummySignal()
    def setChecked(self, v):
        self._checked = bool(v)
    def setToolTip(self, t):
        self._tip = t
    def setStyleSheet(self, s):
        self._style = s


class QPushButton:
    def __init__(self, *args, **kwargs):
        self.clicked = _DummySignal()
        self._checkable = False
        self._checked = False
        self._style = None
        self._tip = None

    def setStyleSheet(self, s):
        self._style = s

    def setCheckable(self, v):
        self._checkable = bool(v)

    def setChecked(self, v):
        if self._checkable:
            self._checked = bool(v)

    def isChecked(self):
        return bool(self._checked)

    def setToolTip(self, t):
        self._tip = t


class QMenu:
    def __init__(self, *args, **kwargs):
        self._actions = []
    def addAction(self, a):
        self._actions.append(a)


class QComboBox:
    def __init__(self, *args, **kwargs):
        self._items = []
        self._current = ''
        self.currentTextChanged = _DummySignal()

    def addItems(self, items):
        try:
            self._items.extend(items)
        except Exception:
            pass

    def setCurrentText(self, txt):
        self._current = txt
        try:
            self.currentTextChanged.emit(self._current)
        except Exception:
            pass

    def currentText(self):
        return self._current
    def setStyleSheet(self, s):
        self._style = s


class QScrollArea:
    def __init__(self, *args, **kwargs):
        self._widget = None
        self._resizable = False
        self._hpolicy = None
        self._vpolicy = None
        self._fixed_height = None

    def setWidget(self, w):
        self._widget = w

    def setWidgetResizable(self, v):
        self._resizable = bool(v)

    def setHorizontalScrollBarPolicy(self, p):
        self._hpolicy = p

    def setVerticalScrollBarPolicy(self, p):
        self._vpolicy = p

    def setFixedHeight(self, h):
        self._fixed_height = h


class QInputDialog:
    @staticmethod
    def getText(parent, title, label):
        return ('', False)


class QMessageBox:
    @staticmethod
    def information(parent, title, message):
        return None


class QDialog:
    def __init__(self, parent=None):
        self._title = ''
        self._minw = None
        self._minh = None

    def exec(self):
        return 0

    def setWindowTitle(self, t):
        self._title = t

    def setMinimumWidth(self, w):
        self._minw = w

    def setMinimumHeight(self, h):
        self._minh = h


class QLineEdit:
    def __init__(self, *args, **kwargs):
        self._text = ''
        self._placeholder = ''

    def setText(self, t):
        self._text = str(t)

    def text(self):
        return self._text

    def setPlaceholderText(self, t):
        self._placeholder = str(t)


class QSizePolicy:
    def __init__(self, *args, **kwargs):
        pass


class QAction:
    def __init__(self, *args, **kwargs):
        pass
