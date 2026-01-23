import sys, os, time
sys.path.insert(0, os.getcwd())
from core.emotes import render_message
from core.signals import signals as emote_signals

received = []

def cb(p):
    print('CB GOT', p)
    received.append(p)

emote_signals.emotes_rendered_ext.connect(cb)
print('connected?', hasattr(emote_signals, 'emotes_rendered_ext'))
try:
    print('top-level signal object id:', id(emote_signals.emotes_rendered_ext))
except Exception:
    pass
try:
    print('callbacks before:', len(getattr(emote_signals.emotes_rendered_ext, '_callbacks', [])))
except Exception:
    print('callbacks before: unknown')
print('Calling render_message...')
print('render_message file:', getattr(render_message, '__code__', None).co_filename)
print(render_message('hello world', None, None))
# small sleep to allow async emit
time.sleep(0.1)
try:
    print('callbacks after:', len(getattr(emote_signals.emotes_rendered_ext, '_callbacks', [])))
except Exception:
    print('callbacks after: unknown')
print('received len', len(received))

# Manual direct emit to verify signal system works
try:
    from core.signals import signals as emote_signals2
    print('manual emit, callbacks:', len(getattr(emote_signals2.emotes_rendered_ext, '_callbacks', [])))
    emote_signals2.emotes_rendered_ext.emit({'manual': True})
    time.sleep(0.05)
    print('received len after manual emit', len(received))
except Exception as ex:
    print('manual emit failed', ex)
