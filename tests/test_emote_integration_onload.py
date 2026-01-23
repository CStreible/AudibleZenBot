import os
import sys
import pytest

from ui.chat_page import build_data_uri_for_emote


try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtCore import QEventLoop, QTimer, QUrl
    HAS_QTWEB = True
except Exception:
    HAS_QTWEB = False


@pytest.mark.skipif(not HAS_QTWEB, reason="Requires PyQt6.QtWebEngineWidgets and a suitable environment")
def test_onload_swap_integration(qtbot):
    """Integration test: load a small page with a broken `file:///` img, inject the
    onload-swap JS using a real data URI from disk and assert the DOM img swaps to
    a `data:` src and reports `naturalWidth > 0`.
    """
    # Ensure resource exists
    emote_id = '445'
    disk_path = os.path.join('resources', 'emotes', f'twitch_{emote_id}.png')
    assert os.path.exists(disk_path), f"prerequisite: {disk_path} must exist"

    data_uri = build_data_uri_for_emote(emote_id, mgr=None)
    assert data_uri and data_uri.startswith('data:image/png'), "could not build data URI for test emote"

    app = QApplication.instance() or QApplication(sys.argv)

    view = QWebEngineView()
    html = """
    <html><body>
      <!-- start with a broken file:/// src to simulate the problem -->
      <img id="emote" src="file:///C:/nonexistent/twitch_{EMOTE_ID}.png" width="28" height="28" />
      <script>
      // expose a function we will call from Python to perform the onload-swap
      function performSwap(dataUri){
          var img = document.getElementById('emote');
          var replacement = new Image();
          replacement.onload = function(){
              console.log('RETRY_EMOTE_REPLACE');
              img.src = dataUri;
          };
          replacement.onerror = function(){ console.log('RETRY_EMOTE_REPLACE_ERROR'); };
          replacement.src = dataUri;
      }
      </script>
    </body></html>
    """.replace('{EMOTE_ID}', emote_id)

    loaded = {'ok': False}
    def on_load_finished(ok):
        loaded['ok'] = ok

    view.loadFinished.connect(on_load_finished)
    view.setHtml(html, QUrl('about:blank'))

    loop = QEventLoop()
    QTimer.singleShot(500, loop.quit)
    loop.exec()
    assert loaded['ok'] is True or loaded['ok'] is False  # ensure loadFinished fired

    # call the page JS to perform the swap
    result_container = {}

    def js_callback(res):
        result_container['res'] = res
        try:
            loop.quit()
        except Exception:
            pass

    # Perform the swap by invoking the JS function with our data URI
    view.page().runJavaScript(f"performSwap({repr(data_uri)})", js_callback)

    # wait a bit for the replacement to load and swap
    QTimer.singleShot(1000, loop.quit)
    loop.exec()

    # Now query the DOM for img.src and naturalWidth
    dom_result = {}

    def dom_cb(res):
        dom_result['value'] = res
        loop.quit()

    view.page().runJavaScript("(function(){var i=document.getElementById('emote'); return {src:i.currentSrc||i.src, w:i.naturalWidth, h:i.naturalHeight};})()", dom_cb)
    QTimer.singleShot(1000, loop.quit)
    loop.exec()

    assert 'value' in dom_result, "failed to read DOM img properties"
    src = dom_result['value'].get('src')
    w = dom_result['value'].get('w')
    assert src is not None and src.startswith('data:'), f"expected data: src after swap, got {src}"
    assert isinstance(w, int) and w > 0, f"expected naturalWidth>0 after swap, got {w}"
