"""User-level settings for FigBox V19."""

import json
import os
from copy import deepcopy


DEFAULT_SETTINGS = {
    "theme": "light",
    "canvas_preset": "A4横版",
    "canvas_width": 297,
    "canvas_height": 210,
    "margin": 5,
    "spacing": 5,
    "grid_size": 5,
    "dpi": 1000,
    "export_format": "PDF矢量",
    "auto_crop": True,
    "label_fontsize": 12,
    "label_visible": True,
    "label_bold": True,
    "label_color": "黑色",
    "label_offset": 0.25,
    "snap_enabled": False,
    "show_guides": False,
    "show_ruler": False,
    "autosave_enabled": True,
    "autosave_interval_minutes": 5,
}


def get_settings_path():
    """Return the per-user V19 settings path."""
    home = os.path.expanduser("~")
    return os.path.join(home, ".figbox", "settings_v19.json")


def _merged_settings(raw_settings):
    """Merge a partial settings dict over defaults."""
    settings = deepcopy(DEFAULT_SETTINGS)
    if isinstance(raw_settings, dict):
        for key, value in raw_settings.items():
            if key in settings:
                settings[key] = value
    return settings


def load_settings(path=None):
    """Load settings from an explicit path, or return defaults when path is None."""
    if path is None:
        return deepcopy(DEFAULT_SETTINGS)
    if not os.path.exists(path):
        return deepcopy(DEFAULT_SETTINGS)
    with open(path, "r", encoding="utf-8") as f:
        return _merged_settings(json.load(f))


def load_user_settings():
    """Load settings from the standard user config location."""
    return load_settings(get_settings_path())


def save_settings(settings, path=None):
    """Save settings after merging them with defaults."""
    if path is None:
        path = get_settings_path()
    merged = _merged_settings(settings)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    return merged
