"""
Save the Extract icon for the Source Engine Asset Manager
"""
import base64
import os

# Icon data (base64 encoded PNG)
ICON_DATA = """
[Base64 data would go here - truncated for brevity]
"""

# Save the icon
with open(os.path.join(os.path.dirname(__file__), 'icon.png'), 'wb') as f:
    f.write(base64.b64decode(ICON_DATA))

print("Icon saved to assets/icon.png")
