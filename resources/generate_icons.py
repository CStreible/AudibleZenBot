"""
Generate placeholder platform icons
Run this script to create simple colored icon files for each platform
"""

from PIL import Image, ImageDraw
import os

# Create icons directory if it doesn't exist
icons_dir = os.path.join(os.path.dirname(__file__), 'icons')
os.makedirs(icons_dir, exist_ok=True)

def create_circle_icon(color, size=32, filename='icon.png'):
    """Create a simple circle icon"""
    # Create image with transparent background
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw circle
    margin = 2
    draw.ellipse([margin, margin, size-margin, size-margin], fill=color)
    
    # Save
    img.save(os.path.join(icons_dir, filename))
    print(f"Created {filename}")

def create_play_icon(size=32, filename='youtube.png'):
    """Create a play button icon for YouTube"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw red circle background
    draw.ellipse([0, 0, size, size], fill='#FF0000')
    
    # Draw white play triangle
    triangle_points = [
        (size * 0.35, size * 0.25),
        (size * 0.35, size * 0.75),
        (size * 0.70, size * 0.5)
    ]
    draw.polygon(triangle_points, fill='white')
    
    img.save(os.path.join(icons_dir, filename))
    print(f"Created {filename}")

# Generate icons for each platform
print("Generating platform icons...")

# Twitch - Purple circle
create_circle_icon('#9146FF', filename='twitch.png')

# YouTube - Red play button
create_play_icon(filename='youtube.png')

# Trovo - Green circle
create_circle_icon('#1ED760', filename='trovo.png')

# Kick - Bright green circle
create_circle_icon('#53FC18', filename='kick.png')

# DLive - Yellow circle
create_circle_icon('#FFD300', filename='dlive.png')

# Twitter - Blue circle
create_circle_icon('#1DA1F2', filename='twitter.png')

print("\nAll icons generated successfully!")
print(f"Icons saved to: {icons_dir}")
print("\nNote: These are placeholder icons. Replace them with official platform logos for production use.")
print("See ICONS_README.md for where to download official logos.")
