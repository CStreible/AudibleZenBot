import importlib
try:
    import requests
    print('requests module repr:', requests)
    print('requests __file__:', getattr(requests,'__file__', None))
    print('requests __name__:', getattr(requests,'__name__', None))
    r2 = importlib.import_module('requests')
    print('importlib.import_module returned:', r2)
    print('importlib __file__:', getattr(r2,'__file__', None))
except Exception as e:
    print('ERROR importing requests:', type(e), e)
