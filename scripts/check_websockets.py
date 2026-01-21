import importlib
try:
    import websockets
    print('websockets module:', websockets)
    print('has connect:', hasattr(websockets, 'connect'))
    try:
        print('connect attr:', getattr(websockets, 'connect'))
    except Exception as e:
        print('connect getattr error:', e)
    print('module file:', getattr(websockets, '__file__', None))
except Exception as e:
    print('import error:', e)
