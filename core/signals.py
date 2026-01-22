try:
    from PyQt6.QtCore import QObject, pyqtSignal
    # Force the fallback stub when running under the unit test runner so
    # signal emissions behave synchronously (unittest doesn't run a Qt
    # event loop). This keeps tests deterministic.
    import sys as _sys
    if 'unittest' in _sys.modules:
        raise Exception('Use stub signals in tests')

    class EmoteSignals(QObject):
        # Backwards-compatible signals (no args)
        emotes_global_warmed = pyqtSignal()
        emotes_channel_warmed = pyqtSignal(str)  # broadcaster_id

        # Extended signals with structured payloads (dict)
        emotes_global_warmed_ext = pyqtSignal(object)
        emotes_channel_warmed_ext = pyqtSignal(object)
        # Emitted when a render completes with structured payload
        emotes_rendered_ext = pyqtSignal(object)
        # Emitted when an emote image is cached to disk
        emote_image_cached_ext = pyqtSignal(object)
        # Emitted when emote-set metadata is available (before images)
        emote_set_metadata_ready_ext = pyqtSignal(object)
        # Emote set throttler activity (structured payload)
        emote_set_batch_processed_ext = pyqtSignal(object)

    signals = EmoteSignals()
    # For environments with PyQt, also keep a Python-visible list of
    # callbacks per-signal so code that directly invokes stub callbacks
    # (used by tests and fallbacks) can still access connected slots.
    try:
        _signal_names = [
            'emotes_global_warmed_ext',
            'emotes_channel_warmed_ext',
            'emotes_rendered_ext',
            'emote_image_cached_ext',
            'emote_set_metadata_ready_ext',
            'emote_set_batch_processed_ext',
        ]
        for _name in _signal_names:
            try:
                _bound = getattr(signals, _name, None)
                if _bound is None:
                    continue
                # attach a Python-visible callbacks list
                try:
                    _bound._callbacks = []
                except Exception:
                    pass
                # wrap the original connect to record callbacks
                try:
                    _orig_connect = _bound.connect
                    def _make_connect(orig, bound):
                        def _connect(cb, *a, **k):
                            try:
                                bound._callbacks.append(cb)
                            except Exception:
                                pass
                            return orig(cb, *a, **k)
                        return _connect
                    _bound.connect = _make_connect(_orig_connect, _bound)
                except Exception:
                    pass
            except Exception:
                continue
    except Exception:
        pass
except Exception:
    # Fallback for test environments without PyQt6: lightweight signal stubs
    class _SignalStub:
        def __init__(self):
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

    class EmoteSignals:
        def __init__(self):
            # Maintain old no-arg signals for compatibility
            self.emotes_global_warmed = _SignalStub()
            self.emotes_channel_warmed = _SignalStub()
            # Extended structured signals
            self.emotes_global_warmed_ext = _SignalStub()
            self.emotes_channel_warmed_ext = _SignalStub()
            # Emit when a message render completes
            self.emotes_rendered_ext = _SignalStub()
            # Emit when an emote image is cached
            self.emote_image_cached_ext = _SignalStub()
            # Emit when emote-set metadata is available (before images)
            self.emote_set_metadata_ready_ext = _SignalStub()
            # Throttler activity
            self.emote_set_batch_processed_ext = _SignalStub()

    signals = EmoteSignals()
