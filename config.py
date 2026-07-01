"""
config.py — Application-wide configuration and display settings.
"""

# Display presets (width, height) in pixels
DISPLAY_PRESETS = {
    "3 inch  (480x320)":  (480, 320),
    "5 inch  (800x480)":  (800, 480),
    "7 inch  (1024x600)": (1024, 600),
    "Custom":             (800, 480),
}

# Default preset key
DEFAULT_PRESET = "5 inch  (800x480)"

# Font scale factor per preset key
FONT_SCALE = {
    "3 inch  (480x320)":  0.75,
    "5 inch  (800x480)":  1.0,
    "7 inch  (1024x600)": 1.3,
    "Custom":             1.0,
}

# Base font sizes (at scale 1.0)
BASE_FONTS = {
    "title":   14,
    "label":   11,
    "button":  10,
    "small":   9,
}

# Row height for test list (pixels)
ROW_HEIGHT = 60

# Colors
COLORS = {
    "bg":         "#f0f0f0",
    "row_even":   "#ffffff",
    "row_odd":    "#f7f7f7",
    "ok":         "#2ecc71",
    "ng":         "#e74c3c",
    "pending":    "#bdc3c7",
    "running":    "#3498db",
    "header_bg":  "#2c3e50",
    "header_fg":  "#ffffff",
}

# Serial mock delay (seconds) to simulate device response
SERIAL_MOCK_DELAY = 1.5
