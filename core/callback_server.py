"""
Shared Callback Server

Provides a single Flask-based HTTP server that other connectors can register
routes with. This allows exposing one local port (e.g. 8889) via ngrok and
routing multiple platform callbacks to different paths instead of each
connector starting its own HTTP server.

API:
 - register_route(path, handler, methods=['POST'])
 - unregister_route(path)
 - start_server(port)
 - is_running()

Handlers receive a Flask `request` object and should return a tuple or
Flask response. This module runs the Flask app in a background thread.
"""

from threading import Thread, Lock
from typing import Callable, Dict, List

try:
    from flask import Flask, request, jsonify
except Exception:
    raise RuntimeError("Flask is required for callback_server. Install with: pip install flask")

_app = Flask(__name__)
_routes: Dict[str, Dict] = {}
_lock = Lock()
_thread: Thread | None = None
_port: int | None = None


def register_route(path: str, handler: Callable, methods: List[str] = None):
    """Register a route with the shared Flask app.

    Args:
        path: URL path (must start with '/')
        handler: Callable that accepts no args (use `request` global) or accepts `request`.
        methods: List of HTTP methods (default ['POST']).
    """
    if not path.startswith('/'):
        path = '/' + path
    if methods is None:
        methods = ['POST']

    with _lock:
        # Normalize endpoint name for Flask (no leading slash)
        endpoint = path.lstrip('/').replace('/', '_') or 'root'

        def _route_func(**kwargs):
            try:
                # Handler may accept request or use flask.request
                res = handler(request)
                if isinstance(res, tuple) or hasattr(res, 'status_code'):
                    return res
                return jsonify({'status': 'ok'})
            except Exception as e:
                import traceback
                traceback.print_exc()
                return (jsonify({'status': 'error', 'error': str(e)}), 500)

        # If endpoint already exists, replace the view function to avoid
        # attempting to re-register the same rule (which raises an error).
        if endpoint in _app.view_functions:
            _app.view_functions[endpoint] = _route_func
            _routes[path] = {'handler': handler, 'methods': methods}
            return

        _app.add_url_rule(path, endpoint=endpoint, view_func=_route_func, methods=methods)
        _routes[path] = {'handler': handler, 'methods': methods}


def unregister_route(path: str):
    if not path.startswith('/'):
        path = '/' + path
    with _lock:
        if path not in _routes:
            return False
        # Flask does not support removing rules at runtime cleanly; mark as removed
        _routes.pop(path, None)
        return True


def start_server(port: int = 8889):
    """Start Flask server in background thread (no-op if already running)."""
    global _thread, _port
    with _lock:
        if _thread and _thread.is_alive() and _port == port:
            return True
        _port = port

        def _run():
            # Suppress werkzeug/flask access logs to reduce noise (127.0.0.1 GET ...)
            try:
                import logging
                logging.getLogger('werkzeug').setLevel(logging.WARNING)
                _app.logger.setLevel(logging.WARNING)
            except Exception:
                pass

            # Bind to all interfaces so ngrok can forward
            try:
                _app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
            except Exception as e:
                print(f"[CallbackServer] Flask server error: {e}")

        _thread = Thread(target=_run, daemon=True)
        _thread.start()
        return True


def is_running() -> bool:
    return _thread is not None and _thread.is_alive()


def get_registered_paths() -> List[str]:
    with _lock:
        return list(_routes.keys())
