"""
slip_config.py — Manages prescription slip layout, font sizes, font styles, reserved area, margins, and horizontal allocations.
"""

import json
import os
import sys
from pathlib import Path

def get_config_file_path() -> Path:
    if getattr(sys, 'frozen', False):
        user_config = Path(sys.executable).parent / "resources" / "slip_config.json"
        if user_config.exists():
            return user_config
        bundled = Path(sys._MEIPASS) / "resources" / "slip_config.json"
        if bundled.exists():
            return bundled
        return user_config
    return Path(__file__).parent.parent / "resources" / "slip_config.json"

CONFIG_FILE = get_config_file_path()

DEFAULT_CONFIG = {
    # ── Margins & Reserved Area ─────────────────────────────────────────────
    "font_family": "Arial",
    "margin_left_mm": 12.0,
    "top_margin_mm": 14.0,
    "reserved_top_area_mm": 0.0,       # Height reserved for pre-printed clinic logo/letterhead
    "show_reserved_area_guide": True,  # Show visual guide in preview for reserved space

    # ── Doctor Information ─────────────────────────────────────────────────
    "doc_name_font_size": 15.0,
    "doc_name_font_style": "Bold",     # Regular, Bold, Italic, Bold Italic
    "doc_name_line_spacing_mm": 6.5,
    
    "degrees_font_size": 8.5,
    "degrees_font_style": "Bold",      # Regular, Bold, Italic, Bold Italic
    "degrees_spacing_mm": 5.0,
    
    "specialization_font_size": 7.5,
    "specialization_font_style": "Regular", # Regular, Bold, Italic, Bold Italic
    "doctor_bottom_spacing_mm": 8.5,

    # ── Patient Information & Allocations ──────────────────────────────────
    "patient_font_size": 9.0,
    "patient_label_style": "Bold",     # Regular, Bold, Italic, Bold Italic
    "patient_value_style": "Regular",  # Regular, Bold, Italic, Bold Italic
    "patient_y_offset_mm": 0.0,
    
    # Horizontal allocation positions (in mm from left edge)
    "name_x_mm": 12.0,
    "gender_x_mm": 44.0,
    "age_x_mm": 68.0,
    "token_x_mm": 88.0,
    "date_x_mm": 112.0,

    # Token badge settings
    "token_font_size": 9.0,
    "token_font_style": "Bold",
    "token_badge_padding_mm": 3.5,
    "token_badge_height_mm": 5.2,
    "show_token_badge": True
}


def load_slip_config() -> dict:
    """Loads prescription slip configuration from JSON, with default fallbacks."""
    config = DEFAULT_CONFIG.copy()
    cfg_file = get_config_file_path()
    if cfg_file.exists():
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                saved = json.load(f)
                if isinstance(saved, dict):
                    config.update(saved)
        except Exception as e:
            print(f"[slip_config] Warning: Failed to load slip_config.json: {e}")
    return config


def save_slip_config(new_config: dict) -> bool:
    """Saves updated configuration to JSON file."""
    try:
        if getattr(sys, 'frozen', False):
            target_file = Path(sys.executable).parent / "resources" / "slip_config.json"
        else:
            target_file = get_config_file_path()
            
        target_file.parent.mkdir(parents=True, exist_ok=True)
        merged = DEFAULT_CONFIG.copy()
        merged.update(new_config)
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=4)
        return True
    except Exception as e:
        print(f"[slip_config] Error saving slip_config.json: {e}")
        return False


def reset_slip_config_to_defaults() -> dict:
    """Resets configuration file to defaults and returns default config."""
    save_slip_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG.copy()
