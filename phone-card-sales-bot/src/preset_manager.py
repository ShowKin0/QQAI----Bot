import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from src.config_loader import merge_env_vars

BASE_DIR = Path(__file__).resolve().parent.parent
PRESETS_DIR = BASE_DIR / "presets"
ACTIVE_FILE = PRESETS_DIR / ".active"
SETTINGS_FILE = BASE_DIR / "config" / "settings.yaml"


class PresetManager:
    """Manage persona presets (CRUD + active selection)."""

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._active_name: Optional[str] = None
        self._ensure_active_file()

    # ── listing ──

    def list_presets(self) -> List[str]:
        """Return preset names (YAML filenames without extension), excluding hidden files."""
        names = []
        for f in PRESETS_DIR.iterdir():
            if f.suffix == ".yaml" and not f.name.startswith("."):
                names.append(f.stem)
        return sorted(names)

    def get_preset(self, name: str) -> Optional[Dict[str, Any]]:
        """Load a preset by name. Returns None if not found."""
        path = PRESETS_DIR / f"{name}.yaml"
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        # Resolve env vars in settings
        settings = data.get("settings", {})
        merge_env_vars(settings)
        data["_name"] = name
        return data

    def save_preset(self, name: str, data: Dict[str, Any]) -> None:
        """Create or update a preset."""
        path = PRESETS_DIR / f"{name}.yaml"
        doc = {
            "name": data.get("name", name),
            "prompt": data.get("prompt", ""),
            "settings": data.get("settings", {}),
        }
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(doc, f, allow_unicode=True, sort_keys=False, indent=2)
        # Invalidate cache
        self._cache.pop(name, None)
        if self._active_name == name:
            self._cache.pop("_active", None)

    def delete_preset(self, name: str) -> bool:
        """Delete a preset file. Cannot delete if it's active."""
        if self.get_active_name() == name:
            return False
        path = PRESETS_DIR / f"{name}.yaml"
        if path.exists():
            path.unlink()
            self._cache.pop(name, None)
            return True
        return False

    # ── active preset ──

    def get_active_name(self) -> str:
        """Return the name of the currently active preset."""
        if self._active_name:
            return self._active_name
        if ACTIVE_FILE.exists():
            self._active_name = ACTIVE_FILE.read_text(encoding="utf-8").strip()
        else:
            presets = self.list_presets()
            self._active_name = presets[0] if presets else "empty-template"
            self._set_active_name(self._active_name)
        return self._active_name

    def set_active(self, name: str) -> bool:
        """Switch to a different preset. Returns False if not found."""
        path = PRESETS_DIR / f"{name}.yaml"
        if not path.exists():
            return False
        self._set_active_name(name)
        self._cache.pop("_active", None)
        self._cache.pop(name, None)
        return True

    def get_active_preset(self) -> Dict[str, Any]:
        """Load the active preset (cached)."""
        if "_active" in self._cache:
            return self._cache["_active"]
        name = self.get_active_name()
        preset = self.get_preset(name)
        if not preset:
            # Fallback to first available
            presets = self.list_presets()
            if presets:
                name = presets[0]
                self._set_active_name(name)
                preset = self.get_preset(name)
        if preset:
            self._cache["_active"] = preset
        return preset or {}

    def reload_active(self) -> Dict[str, Any]:
        """Force reload active preset from disk."""
        self._cache.pop("_active", None)
        return self.get_active_preset()

    # ── helpers ──

    def _set_active_name(self, name: str) -> None:
        self._active_name = name
        ACTIVE_FILE.write_text(name, encoding="utf-8")

    def _ensure_active_file(self) -> None:
        if not ACTIVE_FILE.exists():
            presets = self.list_presets()
            if presets:
                self._set_active_name(presets[0])
