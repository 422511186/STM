"""
SSH Tunnel Manager - GUI Theme System
Custom color theme for light/dark mode support
"""

import customtkinter as ctk

# =============================================================================
# DESIGN TOKENS - Spacing System (base unit: 8px)
# =============================================================================
SPACING_XS = 4
SPACING_SM = 8
SPACING_MD = 16
SPACING_LG = 24
SPACING_XL = 32

# Corner Radius
RADIUS_SM = 6
RADIUS_MD = 10
RADIUS_LG = 16
RADIUS_XL = 20

# Sidebar
SIDEBAR_WIDTH = 220
SIDEBAR_PADDING = 16

# Card
CARD_PADDING = 16
CARD_SPACING = 12

# =============================================================================
# DESIGN TOKENS - Color System (light_mode, dark_mode)
# =============================================================================

# Primary Colors - Blue theme
COLORS = {
    "primary": ("#3B8ED0", "#1F6AA5"),  # Main blue
    "primary_hover": ("#4DA3E8", "#2D7DC2"),  # Lighter blue on hover
    "primary_light": ("#E8F4FC", "#1A3A54"),  # Light blue backgrounds
    # Status Colors
    "success": ("#2D9D4F", "#4ADE80"),  # Green - Active/Success
    "success_bg": ("#E8F9EE", "#1A3D2B"),  # Success background
    "warning": ("#E6A700", "#FBBF24"),  # Orange/Yellow - Connecting/Warning
    "warning_bg": ("#FFF8E6", "#3D3019"),  # Warning background
    "error": ("#D13438", "#EF4444"),  # Red - Error/Stop
    "error_bg": ("#FDECEA", "#3D1A1A"),  # Error background
    "info": ("#3B8ED0", "#60A5FA"),  # Blue - Info/Neutral
    "info_bg": ("#E8F4FC", "#1A3A54"),  # Info background
    # Text Colors
    "text": ("#1A1A1A", "#E5E5E5"),  # Primary text
    "text_secondary": ("#5A5A5A", "#A0A0A0"),  # Secondary text
    "text_muted": ("#8A8A8A", "#6B6B6B"),  # Muted/placeholder text
    # Background Colors
    "bg_main": ("#F5F5F5", "#1A1A1A"),  # Main window background
    "bg_sidebar": ("#FFFFFF", "#252525"),  # Sidebar background
    "bg_card": ("#FFFFFF", "#2D2D2D"),  # Card/tunnel item background
    "bg_input": ("#FFFFFF", "#3A3A3A"),  # Input field background
    "bg_hover": ("#E8E8E8", "#383838"),  # Hover state background
    "bg_modal": ("#FFFFFF", "#2D2D2D"),  # Modal/dialog background
    # Border Colors
    "border": ("#D0D0D0", "#404040"),  # Default border
    "border_focus": ("#3B8ED0", "#60A5FA"),  # Focus state border
    "border_light": ("#E8E8E8", "#383838"),  # Light border for cards
    # Sidebar specific
    "sidebar_accent": ("#3B8ED0", "#1F6AA5"),  # Active nav item
    "sidebar_text": ("#1A1A1A", "#E5E5E5"),  # Sidebar text
    "sidebar_text_muted": ("#6A6A6A", "#888888"),  # Sidebar muted text
}

# =============================================================================
# Font System
# =============================================================================
FONTS = {
    "heading": ("Segoe UI", 20, "bold"),  # Main titles
    "heading_sm": ("Segoe UI", 16, "bold"),  # Section titles
    "body": ("Segoe UI", 14, "normal"),  # Main body text
    "body_sm": ("Segoe UI", 12, "normal"),  # Small body text
    "label": ("Segoe UI", 13, "normal"),  # Form labels
    "mono": ("Cascadia Code", 11, "normal"),  # Monospace (logs)
    "button": ("Segoe UI", 13, "normal"),  # Button text
}


# =============================================================================
# Theme Configuration
# =============================================================================
def configure_theme(theme_name: str = "blue"):
    """Configure CustomTkinter theme"""
    ctk.set_default_color_theme(theme_name)


def apply_fonts(app: ctk.CTk):
    """Apply custom fonts to the app (call after app creation)"""
    # CustomTkinter uses system fonts by default
    # This function reserved for future font customization
    pass


def get_color(key: str) -> tuple:
    """Get color tuple (light_mode, dark_mode)"""
    return COLORS.get(key, ("#000000", "#FFFFFF"))


def get_font(key: str) -> tuple:
    """Get font tuple (family, size, weight)"""
    return FONTS.get(key, ("Segoe UI", 14, "normal"))


# =============================================================================
# Widget Style Helpers
# =============================================================================
def card_style():
    """Returns style kwargs for card-like frames"""
    return {
        "corner_radius": RADIUS_MD,
        "border_width": 1,
        "border_color": COLORS["border"],
        "fg_color": COLORS["bg_card"],
    }


def button_primary_style():
    """Returns style kwargs for primary buttons"""
    return {
        "corner_radius": RADIUS_SM,
        "font": FONTS["button"],
        "height": 36,
    }


def button_secondary_style():
    """Returns style kwargs for secondary buttons"""
    return {
        "corner_radius": RADIUS_SM,
        "font": FONTS["button"],
        "height": 36,
        "fg_color": "transparent",
        "border_width": 1,
        "border_color": COLORS["border"],
    }


def input_style():
    """Returns style kwargs for input fields"""
    return {
        "corner_radius": RADIUS_SM,
        "border_width": 1,
        "fg_color": COLORS["bg_input"],
        "text_color": COLORS["text"],
        "placeholder_text_color": COLORS["text_muted"],
    }


def sidebar_button_style(is_active: bool = False):
    """Returns style kwargs for sidebar buttons (excludes fg_color for flexibility)"""
    base = {
        "corner_radius": RADIUS_SM,
        "text_color": COLORS["primary"] if is_active else COLORS["sidebar_text"],
        "hover_color": COLORS["bg_hover"],
        "anchor": "w",
        "height": 42,
    }
    if is_active:
        base["fg_color"] = COLORS["primary_light"]
    return base
