"""
SSH Tunnel Manager - GUI Theme System
Custom color theme for light/dark mode support
"""

import customtkinter as ctk

SPACING_XS = 4
SPACING_SM = 8
SPACING_MD = 16
SPACING_LG = 24
SPACING_XL = 32

RADIUS_SM = 6
RADIUS_MD = 10
RADIUS_LG = 16
RADIUS_XL = 20

SIDEBAR_WIDTH = 230
SIDEBAR_PADDING = 16

CARD_PADDING = 14
CARD_SPACING = 8

COLORS = {
    "primary": ("#3B82F6", "#3B82F6"),
    "primary_hover": ("#2563EB", "#60A5FA"),
    "primary_light": ("#EFF6FF", "#1E3A5F"),
    "success": ("#10B981", "#34D399"),
    "success_hover": ("#059669", "#6EE7B7"),
    "success_bg": ("#ECFDF5", "#064E3B"),
    "warning": ("#F59E0B", "#FBBF24"),
    "warning_hover": ("#D97706", "#FCD34D"),
    "warning_bg": ("#FFFBEB", "#78350F"),
    "error": ("#EF4444", "#F87171"),
    "error_hover": ("#DC2626", "#FCA5A5"),
    "error_bg": ("#FEF2F2", "#7F1D1D"),
    "error_subtle": ("#FEE2E2", "#5C2020"),
    "info": ("#3B82F6", "#60A5FA"),
    "info_bg": ("#EFF6FF", "#1E3A5F"),
    "text": ("#111827", "#F9FAFB"),
    "text_secondary": ("#4B5563", "#D1D5DB"),
    "text_muted": ("#9CA3AF", "#6B7280"),
    "bg_main": ("#F3F4F6", "#111827"),
    "bg_sidebar": ("#FFFFFF", "#1F2937"),
    "bg_card": ("#FFFFFF", "#1F2937"),
    "bg_input": ("#F9FAFB", "#374151"),
    "bg_hover": ("#F3F4F6", "#374151"),
    "bg_modal": ("#FFFFFF", "#1F2937"),
    "border": ("#D1D5DB", "#4B5563"),
    "border_focus": ("#3B82F6", "#60A5FA"),
    "border_light": ("#E5E7EB", "#374151"),
    "sidebar_accent": ("#3B82F6", "#3B82F6"),
    "sidebar_text": ("#111827", "#F9FAFB"),
    "sidebar_text_muted": ("#6B7280", "#9CA3AF"),
    "sidebar_btn_bg": ("#F3F4F6", "#374151"),
    "sidebar_btn_hover": ("#E5E7EB", "#4B5563"),
}

FONTS = {
    "heading": ("Segoe UI", 18, "bold"),
    "heading_sm": ("Segoe UI", 14, "bold"),
    "body": ("Segoe UI", 13, "normal"),
    "body_sm": ("Segoe UI", 11, "normal"),
    "label": ("Segoe UI", 12, "normal"),
    "mono": ("Cascadia Code", 11, "normal"),
    "button": ("Segoe UI", 12, "normal"),
}


def configure_theme(theme_name: str = "blue"):
    ctk.set_default_color_theme(theme_name)


def apply_fonts(app: ctk.CTk):
    pass


def get_color(key: str) -> tuple:
    return COLORS.get(key, ("#000000", "#FFFFFF"))


def get_font(key: str) -> tuple:
    return FONTS.get(key, ("Segoe UI", 14, "normal"))


def _c(key: str) -> str:
    """Get color for current appearance mode (light or dark)"""
    color_tuple = COLORS.get(key, ("#000000", "#FFFFFF"))
    is_dark = ctk.get_appearance_mode().lower() == "dark"
    return color_tuple[1] if is_dark else color_tuple[0]


def card_style():
    return {
        "corner_radius": RADIUS_MD,
        "border_width": 1,
        "border_color": COLORS["border_light"],
        "fg_color": COLORS["bg_card"],
    }


def button_primary_style():
    return {
        "corner_radius": RADIUS_SM,
        "font": FONTS["button"],
        "height": 36,
    }


def button_secondary_style():
    return {
        "corner_radius": RADIUS_SM,
        "font": FONTS["button"],
        "height": 36,
        "fg_color": "transparent",
        "border_width": 1,
        "border_color": COLORS["border"],
    }


def sidebar_button_style(is_active: bool = False):
    base = {
        "corner_radius": RADIUS_SM,
        "fg_color": COLORS["sidebar_btn_bg"],
        "hover_color": COLORS["sidebar_btn_hover"],
        "text_color": COLORS["primary"] if is_active else COLORS["sidebar_text"],
        "anchor": "center",
        "height": 38,
        "font": FONTS["button"],
    }
    if is_active:
        base["fg_color"] = COLORS["primary_light"]
    return base
