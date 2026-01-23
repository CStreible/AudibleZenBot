import pytest


@pytest.mark.skip(reason="Integration test: requires headless QWebEngine or browser harness")
def test_onload_swap_replaces_only_after_load():
    """Integration skeleton: verify DOM swap only occurs after replacement image `onload` fires.

    TODOs:
    - Drive a headless QWebEngine or browser instance
    - Inject a failing `file:///` src and a replacement data URI
    - Assert that the DOM `<img>` is swapped only after the replacement image `onload` fires
    """
    pass
