import importlib
import sys


def test_secret_store_fallback(monkeypatch):
    # Force non-windows path to exercise fallback implementation
    monkeypatch.setattr(sys, 'platform', 'linux')
    # reload module under test
    import core.secret_store as ss
    importlib.reload(ss)

    # fallback should return plain strings
    s = "mysecret"
    enc = ss.protect_string(s)
    assert enc == s
    dec = ss.unprotect_string(enc)
    assert dec == s
