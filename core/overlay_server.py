"""
Chat Overlay Server for OBS Studio
Provides a web-based chat overlay that syncs with the main application
"""

try:
    from flask import Flask, render_template_string, jsonify, send_file, request  # type: ignore
    from flask_cors import CORS  # type: ignore
    HAS_FLASK = True
except Exception:
    HAS_FLASK = False

# Use the lightweight Qt compatibility layer so this module can be
# imported in headless/test environments without PyQt6 installed.
from platform_connectors.qt_compat import QObject, pyqtSignal, QThread
import threading
import json
import os
import mimetypes
from core.logger import get_logger

logger = get_logger(__name__)

if HAS_FLASK:
    app = Flask(__name__)
    CORS(app)
else:
    # Minimal no-op replacements so route decorators and helpers don't
    # cause import-time failures when Flask isn't installed.
    class _NoOpApp:
        def route(self, *args, **kwargs):
            def _decorator(fn):
                return fn
            return _decorator

        def run(self, *args, **kwargs):
            return None

    def render_template_string(s, **kwargs):
        return s

    def jsonify(obj):
        return obj

    def send_file(path, **kwargs):
        raise RuntimeError("Flask not installed: send_file unavailable")

    class _NoOpRequest:
        def get_data(self, *args, **kwargs):
            return b""

        def get_json(self, *args, **kwargs):
            return None

        headers = {}
        path = '/'

    request = _NoOpRequest()
    def CORS(app):
        return None

    app = _NoOpApp()

# Global state for messages and settings
overlay_messages = []
overlay_lock = threading.Lock()

# Global settings with defaults
overlay_settings = {
    'direction': 'Bottom to Top',
    'max_messages': 50,
    'username_font': 'Arial',
    'username_font_size': 18,
    'message_font': 'Arial',
    'message_font_size': 16,
    'show_badges': True,
    'show_platform': True,
    'entry_animation': 'Slide In',
    'exit_animation': 'Fade Out',
    'duration': 0,
    'msg_opacity': 70,
    'msg_bg_color': '#000000',
    'msg_blur': 10,
    'overlay_bg_type': 'Transparent',
    'overlay_bg_color': '#1a1a1a',
    'overlay_media': '',
    'overlay_device': 'Default Camera'
}
settings_lock = threading.Lock()

# Track last media path to detect changes
last_media_path = ''
media_cache_buster = 0

# Global video devices list
video_devices = []
devices_lock = threading.Lock()


OVERLAY_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chat Overlay</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            background: transparent;
            font-family: 'Segoe UI', Arial, sans-serif;
            overflow: hidden;
            padding: 20px;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        
        body.bg-solid {
            background: var(--overlay-bg-color, #1a1a1a);
        }
        
        body.bg-image {
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
        }
        
        #bg-video {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            object-fit: cover;
            z-index: -1;
        }
        
        #chat-container {
            display: flex;
            gap: 8px;
            overflow: hidden;
            flex: 1;
        }
        
        #chat-container.bottom-to-top {
            flex-direction: column;
            justify-content: flex-end;
        }
        
        #chat-container.top-to-bottom {
            flex-direction: column;
            justify-content: flex-start;
        }
        
        .message {
            border-radius: 8px;
            padding: 12px 16px;
            color: white;
            line-height: 1.4;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
            max-width: 100%;
            word-wrap: break-word;
        }
        }
        
        .message.slide-in {
            animation: slideIn 0.3s ease-out;
        }
        
        .message.fade-in {
            animation: fadeIn 0.4s ease-out;
        }
        
        .message.bounce-in {
            animation: bounceIn 0.5s ease-out;
        }
        
        .message.zoom-in {
            animation: zoomIn 0.3s ease-out;
        }
        
        .message.slide-out {
            animation: slideOut 0.3s ease-out forwards;
        }
        
        .message.fade-out {
            animation: fadeOut 0.3s ease-out forwards;
        }
        
        .message.zoom-out {
            animation: zoomOut 0.3s ease-out forwards;
        }
        
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateX(-20px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }
        
        @keyframes fadeIn {
            from {
                opacity: 0;
            }
            to {
                opacity: 1;
            }
        }
        
        @keyframes bounceIn {
            0% {
                opacity: 0;
                transform: scale(0.3);
            }
            50% {
                transform: scale(1.05);
            }
            70% {
                transform: scale(0.9);
            }
            100% {
                opacity: 1;
                transform: scale(1);
            }
        }
        
        @keyframes zoomIn {
            from {
                opacity: 0;
                transform: scale(0.5);
            }
            to {
                opacity: 1;
                transform: scale(1);
            }
        }
        
        @keyframes slideOut {
            to {
                opacity: 0;
                transform: translateX(20px);
            }
        }
        
        @keyframes fadeOut {
            to {
                opacity: 0;
            }
        }
        
        @keyframes zoomOut {
            to {
                opacity: 0;
                transform: scale(0.5);
            }
        }
        
        .username {
            font-weight: bold;
            margin-right: 8px;
        }
        
        .badges {
            display: inline-flex;
            gap: 4px;
            margin-right: 8px;
            align-items: center;
        }
        
        .badge-img {
            height: 18px;
            width: auto;
            vertical-align: middle;
        }
        
        .platform-icon {
            height: 18px;
            width: 18px;
            vertical-align: middle;
            margin-right: 4px;
        }
        
        .platform {
            display: inline-block;
            background: rgba(255, 255, 255, 0.2);
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 11px;
            margin-right: 8px;
            text-transform: uppercase;
        }
        
        .message-text {
            display: inline;
        }
    </style>
</head>
<body>
    <video id="bg-video" style="display: none;" loop muted autoplay></video>
    <div id="chat-container"></div>
    
    <script>
        const chatContainer = document.getElementById('chat-container');
        const bgVideo = document.getElementById('bg-video');
        let messageElements = new Map();
        let videoStream = null; // Track active video stream
        
        // Settings
        let settings = {
            direction: 'Bottom to Top',
            max_messages: 50,
            username_font: 'Arial',
            username_font_size: 18,
            message_font: 'Arial',
            message_font_size: 16,
            show_badges: true,
            show_platform: true,
            entry_animation: 'Slide In',
            exit_animation: 'Fade Out',
            duration: 0,
            msg_opacity: 70,
            msg_bg_color: '#000000',
            msg_blur: 10,
            overlay_bg_type: 'Transparent',
            overlay_bg_color: '#1a1a1a',
            overlay_media: '',
            overlay_media_url: '',
            overlay_device: 'Default Camera'
        };
        
        // Track message timeouts for duration-based removal
        let messageTimeouts = new Map();
        
        // Track last applied background to avoid resetting video/image unnecessarily
        let lastAppliedBgType = '';
        let lastAppliedMediaUrl = '';
        let lastAppliedDevice = '';
        let lastAppliedDirection = '';
        
        async function applySettings() {
            // Apply direction only if changed
            if (settings.direction !== lastAppliedDirection) {
                chatContainer.className = settings.direction === 'Top to Bottom' ? 'top-to-bottom' : 'bottom-to-top';
                lastAppliedDirection = settings.direction;
            }
            
            // Only update background if type, media URL, or device changed
            const bgTypeChanged = settings.overlay_bg_type !== lastAppliedBgType;
            const mediaUrlChanged = settings.overlay_media_url !== lastAppliedMediaUrl;
            const deviceChanged = settings.overlay_device !== lastAppliedDevice;
            
            // Absolutely do not touch video if nothing changed
            if (!bgTypeChanged && !mediaUrlChanged && !deviceChanged) {
                // Only update solid color if that's the current type
                if (settings.overlay_bg_type === 'Solid Color') {
                    document.body.style.setProperty('--overlay-bg-color', settings.overlay_bg_color);
                }
                return; // Exit early - nothing to do
            }
            
            // Clear old background only if we're actually changing types
            if (bgTypeChanged) {
                document.body.className = '';
                document.body.style.backgroundImage = '';
                
                // Stop video stream if switching away from video device
                if (lastAppliedBgType === 'Video Device' && videoStream) {
                    videoStream.getTracks().forEach(track => track.stop());
                    videoStream = null;
                }
                
                if (lastAppliedBgType === 'Video' || lastAppliedBgType === 'Video Device') {
                    bgVideo.pause();
                    bgVideo.style.display = 'none';
                    bgVideo.src = '';
                    bgVideo.srcObject = null;
                }
            }
            
            // Also stop video stream when changing devices (even if type hasn't changed)
            if (deviceChanged && settings.overlay_bg_type === 'Video Device' && videoStream) {
                videoStream.getTracks().forEach(track => track.stop());
                videoStream = null;
                bgVideo.pause();
                bgVideo.srcObject = null;
            }
            
            // Apply new background
            if (settings.overlay_bg_type === 'Solid Color') {
                document.body.className = 'bg-solid';
                document.body.style.setProperty('--overlay-bg-color', settings.overlay_bg_color);
            } else if (settings.overlay_bg_type === 'Image' && settings.overlay_media_url) {
                document.body.className = 'bg-image';
                document.body.style.backgroundImage = `url("${settings.overlay_media_url}")`;
            } else if (settings.overlay_bg_type === 'Video' && settings.overlay_media_url) {
                // Only set video if URL actually changed
                if (mediaUrlChanged) {
                    bgVideo.srcObject = null;
                    bgVideo.src = settings.overlay_media_url;
                    bgVideo.load();
                }
                bgVideo.style.display = 'block';
            } else if (settings.overlay_bg_type === 'Video Device') {
                // Access user's video device
                try {
                    // Parse device ID from settings (format: "DeviceName|deviceId")
                    let deviceConstraint = true;  // Default: any camera
                    
                    if (settings.overlay_device && settings.overlay_device.includes('|')) {
                        const deviceId = settings.overlay_device.split('|')[1];
                        const deviceName = settings.overlay_device.split('|')[0];
                        
                        // Check if deviceId is numeric (from Python/OpenCV) or a string (from browser)
                        if (/^\\d+$/.test(deviceId)) {
                            // Numeric index from Python - enumerate browser devices and match by name
                            const targetIndex = parseInt(deviceId);
                            console.log(`[Overlay] Looking for camera: ${deviceName} (Python index ${targetIndex})`);
                            
                            try {
                                const devices = await navigator.mediaDevices.enumerateDevices();
                                const videoDevices = devices.filter(d => d.kind === 'videoinput');
                                console.log(`[Overlay] Browser found ${videoDevices.length} video devices:`, videoDevices.map(d => d.label || 'Unnamed'));
                                
                                // First try to match by device name (most reliable)
                                let matchedDevice = null;
                                
                                // Try exact name match first
                                matchedDevice = videoDevices.find(d => d.label && d.label === deviceName);
                                
                                // If no exact match, try partial match (device name contains or is contained in label)
                                if (!matchedDevice) {
                                    matchedDevice = videoDevices.find(d => {
                                        if (!d.label) return false;
                                        const label = d.label.toLowerCase();
                                        const name = deviceName.toLowerCase();
                                        // Check if either string contains the other
                                        return label.includes(name) || name.includes(label);
                                    });
                                }
                                
                                // Fallback to index if name matching fails
                                if (!matchedDevice && targetIndex < videoDevices.length) {
                                    matchedDevice = videoDevices[targetIndex];
                                    console.log(`[Overlay] No name match, using index ${targetIndex}: ${matchedDevice.label}`);
                                }
                                
                                if (matchedDevice) {
                                    deviceConstraint = { deviceId: { exact: matchedDevice.deviceId } };
                                    console.log(`[Overlay] Matched device: ${matchedDevice.label}`);
                                } else {
                                    console.warn(`[Overlay] Could not find device "${deviceName}". Using default camera.`);
                                }
                            } catch (enumError) {
                                console.warn(`[Overlay] Could not enumerate devices:`, enumError);
                                console.log(`[Overlay] Falling back to default camera`);
                            }
                        } else {
                            // Browser deviceId string - use exact match
                            deviceConstraint = { deviceId: { exact: deviceId } };
                        }
                    }
                    
                    const constraints = { 
                        video: deviceConstraint,
                        audio: false 
                    };
                    
                    const stream = await navigator.mediaDevices.getUserMedia(constraints);
                    videoStream = stream;
                    bgVideo.src = '';
                    bgVideo.srcObject = stream;
                    bgVideo.play();
                    bgVideo.style.display = 'block';
                } catch (error) {
                    console.error('Error accessing video device:', error);
                    alert('Could not access video device. Please check your camera permissions and that the selected device is available.');
                }
            }
            
            lastAppliedBgType = settings.overlay_bg_type;
            lastAppliedMediaUrl = settings.overlay_media_url;
            lastAppliedDevice = settings.overlay_device;
        }
        
        function getAnimationClass(type) {
            const entryMap = {
                'Slide In': 'slide-in',
                'Fade In': 'fade-in',
                'Bounce In': 'bounce-in',
                'Zoom In': 'zoom-in',
                'None': ''
            };
            const exitMap = {
                'Slide Out': 'slide-out',
                'Fade Out': 'fade-out',
                'Zoom Out': 'zoom-out',
                'None': ''
            };
            if (type === 'entry') {
                return entryMap[settings.entry_animation] || '';
            } else if (type === 'exit') {
                return exitMap[settings.exit_animation] || '';
            }
            return '';
        }
        
        function addMessage(msg) {
            // Remove if already exists
            if (messageElements.has(msg.id)) {
                removeMessage(msg.id);
            }
            
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message';
            const animClass = getAnimationClass('entry');
            if (animClass) {
                messageDiv.classList.add(animClass);
            }
            messageDiv.dataset.id = msg.id;
            
            // Apply message background styling
            const opacity = settings.msg_opacity / 100;
            const bgColor = settings.msg_bg_color;
            const blur = settings.msg_blur;
            messageDiv.style.background = `rgba(${parseInt(bgColor.slice(1,3), 16)}, ${parseInt(bgColor.slice(3,5), 16)}, ${parseInt(bgColor.slice(5,7), 16)}, ${opacity})`;
            if (blur > 0) {
                messageDiv.style.backdropFilter = `blur(${blur}px)`;
            }
            
            // Platform icon
            let platformIconHTML = '';
            if (settings.show_platform) {
                if (msg.platform_icon) {
                    platformIconHTML = `<img src="${msg.platform_icon}" class="platform-icon" alt="${msg.platform}" />`;
                } else {
                    platformIconHTML = `<span class="platform">${msg.platform}</span>`;
                }
            }
            
            // Badges
            let badgesHTML = '';
            if (settings.show_badges && msg.badges && msg.badges.length > 0) {
                badgesHTML = '<span class="badges">' + 
                    msg.badges.map(b => {
                        if (b.url) {
                            return `<img src="${b.url}" class="badge-img" alt="${b.name}" title="${b.name}" />`;
                        } else {
                            return `<span class="badge ${b.name}">${b.name}</span>`;
                        }
                    }).join('') +
                    '</span>';
            }
            
            // Apply fonts
            const usernameStyle = `font-family: ${settings.username_font}; font-size: ${settings.username_font_size}px;`;
            const messageStyle = `font-family: ${settings.message_font}; font-size: ${settings.message_font_size}px;`;
            
            messageDiv.innerHTML = `
                ${platformIconHTML}
                ${badgesHTML}
                <span class="username" style="${usernameStyle} color: ${msg.color || '#ffffff'};">${msg.username}:</span>
                <span class="message-text" style="${messageStyle}">${escapeHtml(msg.message)}</span>
            `;
            
            // Add to container based on direction
            if (settings.direction === 'Top to Bottom') {
                chatContainer.appendChild(messageDiv);
            } else {
                chatContainer.appendChild(messageDiv);
            }
            
            messageElements.set(msg.id, messageDiv);
            
            // Set timeout for duration-based removal (if duration > 0)
            if (settings.duration > 0) {
                const timeoutId = setTimeout(() => {
                    removeMessage(msg.id, true);
                }, settings.duration * 1000);
                messageTimeouts.set(msg.id, timeoutId);
            }
            
            // Keep only last N messages
            while (chatContainer.children.length > settings.max_messages) {
                const firstChild = chatContainer.firstChild;
                const firstId = firstChild.dataset.id;
                removeMessage(firstId, false);
            }
            
            // Scroll to show new message
            if (settings.direction === 'Top to Bottom') {
                messageDiv.scrollIntoView({ behavior: 'smooth', block: 'end' });
            } else {
                messageDiv.scrollIntoView({ behavior: 'smooth', block: 'end' });
            }
        }
        
        function removeMessage(messageId, useExitAnimation = true) {
            // Clear any pending timeout
            if (messageTimeouts.has(messageId)) {
                clearTimeout(messageTimeouts.get(messageId));
                messageTimeouts.delete(messageId);
            }
            
            const element = messageElements.get(messageId);
            if (element) {
                if (useExitAnimation) {
                    const exitClass = getAnimationClass('exit');
                    if (exitClass) {
                        element.classList.add(exitClass);
                        setTimeout(() => {
                            element.remove();
                            messageElements.delete(messageId);
                        }, 300);
                    } else {
                        // No exit animation, remove immediately
                        element.remove();
                        messageElements.delete(messageId);
                    }
                } else {
                    // Forced removal without animation (e.g., max messages exceeded)
                    element.remove();
                    messageElements.delete(messageId);
                }
            }
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        // Poll for settings
        async function pollSettings() {
            try {
                const response = await fetch('/overlay/settings');
                const data = await response.json();
                if (data.settings) {
                    const newSettings = data.settings;
                    
                    // Check specific fields that require action
                    const needsUpdate = 
                        settings.direction !== newSettings.direction ||
                        settings.max_messages !== newSettings.max_messages ||
                        settings.username_font !== newSettings.username_font ||
                        settings.username_font_size !== newSettings.username_font_size ||
                        settings.message_font !== newSettings.message_font ||
                        settings.message_font_size !== newSettings.message_font_size ||
                        settings.show_badges !== newSettings.show_badges ||
                        settings.show_platform !== newSettings.show_platform ||
                        settings.entry_animation !== newSettings.entry_animation ||
                        settings.exit_animation !== newSettings.exit_animation ||
                        settings.duration !== newSettings.duration ||
                        settings.msg_opacity !== newSettings.msg_opacity ||
                        settings.msg_bg_color !== newSettings.msg_bg_color ||
                        settings.msg_blur !== newSettings.msg_blur ||
                        settings.overlay_bg_type !== newSettings.overlay_bg_type ||
                        settings.overlay_bg_color !== newSettings.overlay_bg_color ||
                        settings.overlay_media_url !== newSettings.overlay_media_url ||
                        settings.overlay_device !== newSettings.overlay_device;
                    
                    // If duration changed, need to clear existing timeouts and reapply
                    if (settings.duration !== newSettings.duration) {
                        // Clear all existing message timeouts
                        messageTimeouts.forEach(timeoutId => clearTimeout(timeoutId));
                        messageTimeouts.clear();
                        
                        // Reapply timeouts if new duration > 0
                        if (newSettings.duration > 0) {
                            messageElements.forEach((element, id) => {
                                const timeoutId = setTimeout(() => {
                                    removeMessage(id, true);
                                }, newSettings.duration * 1000);
                                messageTimeouts.set(id, timeoutId);
                            });
                        }
                    }
                    
                    // Debug logging
                    if (needsUpdate && settings.overlay_bg_type === 'Video') {
                        console.log('Settings changed - Video background:');
                        console.log('  Old URL:', settings.overlay_media_url);
                        console.log('  New URL:', newSettings.overlay_media_url);
                        console.log('  URLs match:', settings.overlay_media_url === newSettings.overlay_media_url);
                    }
                    
                    settings = newSettings;
                    
                    // Only apply settings if something actually changed
                    if (needsUpdate) {
                        console.log('Applying settings update');
                        applySettings();
                    }
                }
            } catch (error) {
                console.error('Error polling settings:', error);
            }
        }
        
        // Enumerate video devices and send to backend
        async function enumerateVideoDevices() {
            console.log('[Overlay] Starting device enumeration...');
            try {
                // Request permission first to get device labels
                console.log('[Overlay] Requesting camera permission...');
                const tempStream = await navigator.mediaDevices.getUserMedia({ video: true });
                tempStream.getTracks().forEach(track => track.stop());
                console.log('[Overlay] Permission granted, enumerating devices...');
                
                const devices = await navigator.mediaDevices.enumerateDevices();
                const videoDevices = devices
                    .filter(device => device.kind === 'videoinput')
                    .map(device => ({
                        label: device.label || `Camera ${device.deviceId.substr(0, 8)}`,
                        deviceId: device.deviceId
                    }));
                
                console.log(`[Overlay] Found ${videoDevices.length} video devices:`, videoDevices);
                
                // Send device list to backend
                if (videoDevices.length > 0) {
                    console.log('[Overlay] Sending devices to backend...');
                    const response = await fetch('/overlay/devices', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ devices: videoDevices })
                    });
                    console.log('[Overlay] Backend response:', await response.json());
                }
            } catch (error) {
                console.error('[Overlay] Could not enumerate video devices:', error);
            }
        }
        
        // Poll for messages
        let lastUpdate = Date.now();
        
        async function pollMessages() {
            try {
                const response = await fetch(`/overlay/messages?since=${lastUpdate}`);
                const data = await response.json();
                
                if (data.messages) {
                    data.messages.forEach(msg => {
                        if (msg.action === 'add') {
                            addMessage(msg);
                        } else if (msg.action === 'remove') {
                            removeMessage(msg.id);
                        }
                    });
                }
                
                lastUpdate = Date.now();
            } catch (error) {
                console.error('Error polling messages:', error);
            }
            
            setTimeout(pollMessages, 500);
        }
        
        // Initial setup
        pollSettings();
        setInterval(pollSettings, 1000);  // Poll settings every second
        pollMessages();
        enumerateVideoDevices();  // Enumerate available video devices
    </script>
</body>
</html>
"""


@app.route('/')
@app.route('/overlay')
def overlay():
    """Serve the chat overlay HTML"""
    return render_template_string(OVERLAY_HTML)


@app.route('/overlay/messages')
def get_messages():
    """Get recent messages for the overlay"""
    with overlay_lock:
        # Return all pending messages and clear the queue
        messages = overlay_messages.copy()
        overlay_messages.clear()
        return jsonify({'messages': messages})


@app.route('/overlay/settings')
def get_settings():
    """Get current overlay settings"""
    global last_media_path, media_cache_buster
    with settings_lock:
        settings = overlay_settings.copy()
        # Convert file path to URL if media is set
        # Only update cache buster when media path actually changes to prevent flickering
        current_media = settings.get('overlay_media', '')
        if current_media != last_media_path:
            import time
            last_media_path = current_media
            media_cache_buster = int(time.time() * 1000)
        
        if current_media:
            settings['overlay_media_url'] = f'/overlay/media?t={media_cache_buster}'
        else:
            settings['overlay_media_url'] = ''
        return jsonify({'settings': settings})


@app.route('/overlay/media')
def serve_media():
    """Serve the overlay background media file"""
    with settings_lock:
        media_path = overlay_settings.get('overlay_media', '')
        if media_path and os.path.exists(media_path):
            return send_file(media_path, mimetype=mimetypes.guess_type(media_path)[0])
        return '', 404


@app.route('/overlay/devices', methods=['POST'])
def receive_devices():
    """Receive list of video devices from browser"""
    global video_devices
    try:
        data = request.json
        device_list = data.get('devices', [])
        
        # Format devices as "Name|deviceId" strings for the dropdown
        formatted_devices = []
        for device in device_list:
            label = device.get('label', 'Unknown Camera')
            device_id = device.get('deviceId', '')
            if device_id:
                formatted_devices.append(f"{label}|{device_id}")
        
        with devices_lock:
            video_devices = formatted_devices
        
        logger.info(f"Received {len(formatted_devices)} video devices")
        
        # Signal the UI to update (will be implemented)
        if server_instance:
            server_instance.devices_updated.emit(formatted_devices)
        
        return jsonify({'status': 'ok', 'count': len(formatted_devices)})
    except Exception as e:
        logger.exception(f"Error receiving devices: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


def update_overlay_settings(new_settings):
    """Update overlay settings"""
    with settings_lock:
        overlay_settings.update(new_settings)
        logger.info(f"Settings updated: {new_settings}")



def add_overlay_message(platform, username, message, message_id, badges=None, color=None):
    """Add a message to the overlay"""
    from ui.platform_icons import get_platform_icon_html
    from ui.chat_page import get_badge_html
    import re
    
    with overlay_lock:
        # Get platform icon HTML and extract the data URI
        platform_icon_html = get_platform_icon_html(platform, size=18)
        platform_icon_url = ''
        if platform_icon_html:
            # Extract src from img tag
            match = re.search(r'src="([^"]+)"', platform_icon_html)
            if match:
                platform_icon_url = match.group(1)
        
        # Convert badge names to badge image URLs
        badge_urls = []
        if badges:
            for badge in badges:
                badge_html = get_badge_html(badge, platform)
                if badge_html:
                    # Extract src from img tag
                    match = re.search(r'src="([^"]+)"', badge_html)
                    if match:
                        badge_urls.append({
                            'url': match.group(1),
                            'name': badge.split('/')[0] if '/' in str(badge) else str(badge)
                        })
        
        msg = {
            'action': 'add',
            'id': message_id,
            'platform': platform,
            'platform_icon': platform_icon_url,
            'username': username,
            'message': message,
            'badges': badge_urls,
            'color': color,
            'timestamp': threading.current_thread().ident
        }
        overlay_messages.append(msg)
        
        # Keep only last 100 events
        if len(overlay_messages) > 100:
            overlay_messages.pop(0)


def remove_overlay_message(message_id):
    """Remove a message from the overlay"""
    with overlay_lock:
        msg = {
            'action': 'remove',
            'id': message_id,
            'timestamp': threading.current_thread().ident
        }
        overlay_messages.append(msg)
        
        # Keep only last 100 events
        if len(overlay_messages) > 100:
            overlay_messages.pop(0)


class OverlayServer(QObject):
    """Manages the Flask overlay server in a separate thread"""
    server_started = pyqtSignal(str)  # Emits the overlay URL
    devices_updated = pyqtSignal(list)  # Emits list of video devices
    
    def __init__(self, port=5000):
        super().__init__()
        self.port = port
        self.server_thread = None
        
    def start(self):
        """Start the Flask server in a background thread"""
        def run_server():
            app.run(host='0.0.0.0', port=self.port, debug=False, use_reloader=False)
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()

        # Emit the overlay URL
        overlay_url = f"http://localhost:{self.port}/overlay"
        self.server_started.emit(overlay_url)
        logger.info(f"Started on {overlay_url}")
        
    def add_message(self, platform, username, message, message_id, badges=None, color=None):
        """Add a message to the overlay"""
        add_overlay_message(platform, username, message, message_id, badges, color)
        
    def remove_message(self, message_id):
        """Remove a message from the overlay"""
        remove_overlay_message(message_id)
    
    def update_settings(self, settings):
        """Update overlay settings"""
        update_overlay_settings(settings)
