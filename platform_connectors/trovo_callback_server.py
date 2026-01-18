"""
Compatibility layer for Trovo OAuth callback using the shared callback server.

This module preserves the small public surface expected by other parts of the
codebase (`last_code_event`, `last_code_container`, and an `app.run()` helper)
but registers a route on `core.callback_server` instead of creating its own
Flask process. This avoids multiple Flask servers and allows a single ngrok
tunnel to be shared across platforms.
"""

import threading
from typing import Any
from core.logger import get_logger

logger = get_logger(__name__)

last_code_event = threading.Event()
last_code_container: dict[str, Any] = {}


class _CompatApp:
    """Tiny compatibility wrapper exposing a `run(host, port, ...)` method.

    Calling `run()` will register the `/callback` route on the shared
    `core.callback_server` and start the shared server on the specified port.
    """

    def run(self, host='0.0.0.0', port: int = 8889, debug: bool = False, use_reloader: bool = False):
        try:
            from core import callback_server

            def _handler(req):
                # Extract 'code' from query parameters
                try:
                    code = req.args.get('code')
                except Exception:
                    code = None
                logger.debug(f"[Trovo OAuth] Received callback with code: {code}")
                if code:
                    last_code_container['code'] = code
                    try:
                        last_code_event.set()
                    except Exception:
                        pass
                    return (f"Authorization code received: <b>{code}</b><br>You may close this window and return to AudibleZenBot.", 200)
                return ("No authorization code found in the request.", 400)

            # Register the route (idempotent) and start server
            callback_server.register_route('/callback', _handler, methods=['GET'])
            callback_server.start_server(port)
            logger.info(f"[Trovo Callback] Registered /callback on shared server (port {port})")
        except Exception as e:
            logger.exception(f"[Trovo Callback] Failed to register callback route: {e}")


# Provide the small API the rest of the code expects
app = _CompatApp()


if __name__ == '__main__':
    app.run(port=8889)
