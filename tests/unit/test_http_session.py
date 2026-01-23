import importlib


def test_make_retry_session_minimal_interface():
    import core.http_session as hs
    importlib.reload(hs)

    sess = hs.make_retry_session()
    # Session fallback or real requests.Session both should provide .get
    assert hasattr(sess, 'get')
