import sys
print('sys.path[0]=', sys.path[0])
try:
    import websockets
    print('imported websockets:', websockets)
    print('websockets.__file__:', getattr(websockets, '__file__', None))
    print('has connect:', hasattr(websockets, 'connect'))
    print('connect:', getattr(websockets, 'connect', None))
except Exception as e:
    print('ERROR importing websockets:', type(e), e)
    import traceback; traceback.print_exc()
