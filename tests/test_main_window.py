import os
import sys
import unittest

try:
    # Prefer installed PyQt6 in test environments like other tests
    import sysconfig
    purelib = sysconfig.get_paths().get('purelib')
    if purelib and purelib not in sys.path:
        sys.path.insert(0, purelib)
except Exception:
    pass

try:
    from PyQt6.QtWidgets import QApplication
    HAS_PYQT = True
except Exception:
    HAS_PYQT = False


@unittest.skipIf(not HAS_PYQT, "PyQt6 not available in this environment")
class MainWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Ensure Qt is configured for WebEngine before creating Q(Core)Application
        try:
            from PyQt6.QtCore import Qt, QCoreApplication
            QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
        except Exception:
            pass
        import sys as _sys
        argv = list(_sys.argv) or [_sys.executable]
        cls._app = QApplication.instance() or QApplication(argv)

    def test_mainwindow_constructs_ci_mode(self):
        # Ensure CI mode skips heavy connector instantiation
        os.environ['AUDIBLEZENBOT_CI'] = '1'

        # Import main after setting env so ChatManager honors CI flag
        import importlib
        if 'main' in sys.modules:
            importlib.reload(sys.modules['main'])
        main = importlib.import_module('main')

        # Construct MainWindow (should not raise)
        w = main.MainWindow()

        # Basic smoke assertions
        self.assertTrue(hasattr(w, 'pages'))
        self.assertIn('chat', w.pages)
        self.assertIn('connections', w.pages)
        self.assertIn('settings', w.pages)
        self.assertIn('overlay', w.pages)
        self.assertIn('automation', w.pages)
        self.assertTrue(hasattr(w, 'sidebar'))


if __name__ == '__main__':
    unittest.main()
