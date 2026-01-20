import importlib
from pathlib import Path


def test_log_manager_start_stop(tmp_path):
    # Import under test
    from core.logger import LogManager

    class FakeConfig:
        def __init__(self):
            self._m = {}

        def get(self, k, default=None):
            return self._m.get(k, default)

        def set(self, k, v):
            self._m[k] = v

    cfg = FakeConfig()
    lm = LogManager(config=cfg)

    # set a temporary log folder and start logging
    lm.set_log_folder(str(tmp_path))
    assert lm.get_log_folder() == str(tmp_path)
    assert lm.start_logging() is True
    assert lm.is_enabled() is True

    # verify file path
    lp = lm.get_log_path()
    assert lp is not None
    assert Path(lp).parent.exists()

    # disable and cleanup
    lm.stop_logging()
    assert lm.is_enabled() is False
    lm.cleanup()
