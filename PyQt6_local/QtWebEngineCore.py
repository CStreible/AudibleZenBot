class QWebEngineScript:
    DocumentReady = 0
    class InjectionPoint:
        DocumentReady = 0

    class ScriptWorldId:
        MainWorld = 0
        ApplicationWorld = 1

    def __init__(self, *args, **kwargs):
        self._name = None
        self._injection_point = None
        self._world_id = None
        self._source = None

    def setName(self, name):
        self._name = name

    def setInjectionPoint(self, ip):
        self._injection_point = ip

    def setWorldId(self, wid):
        self._world_id = wid

    def setSourceCode(self, src):
        self._source = src
