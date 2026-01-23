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
