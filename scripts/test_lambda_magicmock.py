from unittest.mock import MagicMock

def side_effect(batch):
    print('SIDE_EFFECT called with', batch)

mm = MagicMock(side_effect=side_effect)
b = ['1','2','3']
bound = (lambda b=b, f=mm: f(b))
print('bound repr', repr(bound))
bound()
print('done')
