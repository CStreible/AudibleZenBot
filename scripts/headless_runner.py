from core.config import ConfigManager
from core.ngrok_manager import NgrokManager
from core.chat_manager import ChatManager
from core.overlay_server import OverlayServer
from core.logger import get_log_manager

print('[Headless-Runner] Creating ConfigManager')
config = ConfigManager()
print('[Headless-Runner] Creating NgrokManager')
ngrok_manager = NgrokManager(config)
print('[Headless-Runner] Creating ChatManager')
chat_manager = ChatManager(config)
chat_manager.ngrok_manager = ngrok_manager
print('[Headless-Runner] Creating OverlayServer')
overlay_server = OverlayServer(port=5000)
print('[Headless-Runner] Initializing log manager')
log_manager = get_log_manager(config)
try:
    from core.twitch_emotes import get_manager as get_twitch_manager
    try:
        get_twitch_manager().prefetch_global(background=False)
        print('[Headless-Runner] Twitch prefetch requested')
    except Exception as e:
        print('[Headless-Runner] Twitch prefetch failed:', e)
except Exception:
    print('[Headless-Runner] Twitch emote manager not available')
print('[Headless-Runner] Headless initialization complete')
