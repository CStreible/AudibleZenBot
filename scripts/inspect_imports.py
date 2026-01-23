import sys, traceback
print('sys.executable:', sys.executable)
print('sys.path:')
for p in sys.path:
    print('  ', p)
try:
    import requests
    print('Imported requests:', requests)
    print('requests.__file__:', getattr(requests, '__file__', None))
except Exception as e:
    print('Import failed:', type(e), e)
    traceback.print_exc()
