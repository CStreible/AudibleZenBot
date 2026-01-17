# Platform icon utilities for chat UI

# Placeholder for get_platform_icon_html and PLATFORM_COLORS

def get_platform_icon_html(platform: str, size: int = 18) -> str:
    """Return HTML for platform icon image."""
    import os, base64, sys
    
    # Get base directory (works for both script and PyInstaller)
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        base_dir = sys._MEIPASS
    else:
        # Running as script
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Map platforms to local image files (PNG, JPG/JPEG, or SVG)
    platform_image_map = {
        'kick': os.path.join(base_dir, 'resources', 'badges', 'kick', 'kick_logo.jpg'),  # JPG file
        'youtube': os.path.join(base_dir, 'resources', 'badges', 'youtube', 'youtube_logo.svg'),
        'dlive': os.path.join(base_dir, 'resources', 'badges', 'dlive', 'dlive_logo.png'),  # PNG file
        'trovo': os.path.join(base_dir, 'resources', 'icons', 'trovo.ico'),
    }
    
    # Try to load local image first
    image_path = platform_image_map.get(platform)
    if image_path and os.path.exists(image_path):
        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()
            b64 = base64.b64encode(image_data).decode('utf-8')
            
            # Determine MIME type based on file extension
            if image_path.endswith('.png'):
                mime_type = 'image/png'
            elif image_path.endswith('.svg'):
                mime_type = 'image/svg+xml'
            elif image_path.endswith('.jpg') or image_path.endswith('.jpeg'):
                mime_type = 'image/jpeg'
            elif image_path.endswith('.ico'):
                mime_type = 'image/x-icon'
            else:
                mime_type = 'image/png'  # default
            
            data_uri = f'data:{mime_type};base64,{b64}'
            return f'<img src="{data_uri}" width="{size}" height="{size}" style="vertical-align: middle; margin-right: 2px;" />'
        except Exception as e:
            print(f"Error loading icon for {platform}: {e}")
    
    # Fallback to external URL
    icon_url = PLATFORM_COLORS.get(platform, '')
    if not icon_url:
        return ''
    return f'<img src="{icon_url}" width="{size}" height="{size}" style="vertical-align: middle; margin-right: 2px;" />'

# Example color/icon mapping for platforms
PLATFORM_COLORS = {
    'twitch': 'https://static.twitchcdn.net/assets/favicon-32-e29e246c157142c94346.png',
    'kick': 'https://static.kick.com/favicon.ico',
    'youtube': 'https://www.youtube.com/s/desktop/6e8e7e7d/img/favicon_32x32.png',
    'trovo': 'https://trovo.live/favicon.ico',
    'dlive': 'https://dlive.tv/favicon.ico',
    'twitter': 'https://abs.twimg.com/favicons/twitter.ico',
}
