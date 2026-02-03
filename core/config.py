"""
Configuration management for Claude Code Manager.
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any


class Config:
    """Application configuration manager."""

    def __init__(self):
        self.claude_dir = self._find_claude_dir()
        self.projects_dir = self.claude_dir / "projects"
        self.plugins_dir = self.claude_dir / "plugins"
        self.todos_dir = self.claude_dir / "todos"
        self.cache_dir = self.claude_dir / "cache"
        self.settings_file = self.claude_dir / "settings.json"
        self.config_file = self.claude_dir / "config.json"
        self.stats_cache_file = self.claude_dir / "stats-cache.json"
        self.history_file = self.claude_dir / "history.jsonl"

        # Claude Desktop config path
        if os.name == 'nt':  # Windows
            appdata = os.environ.get('APPDATA', '')
            self.claude_desktop_config = Path(appdata) / "Claude" / "claude_desktop_config.json"
        else:  # macOS/Linux
            self.claude_desktop_config = Path.home() / ".config" / "claude" / "claude_desktop_config.json"

        self._settings: Optional[Dict[str, Any]] = None
        self._config: Optional[Dict[str, Any]] = None

    def _find_claude_dir(self) -> Path:
        """Find the .claude directory."""
        # Check common locations
        home = Path.home()
        possible_paths = [
            home / ".claude",
            Path(os.environ.get('USERPROFILE', '')) / ".claude",
        ]

        for path in possible_paths:
            if path.exists():
                return path

        # Default to home directory
        return home / ".claude"

    @property
    def settings(self) -> Dict[str, Any]:
        """Load and return settings."""
        if self._settings is None:
            self._settings = self._load_json(self.settings_file, {})
        return self._settings

    @property
    def config(self) -> Dict[str, Any]:
        """Load and return config."""
        if self._config is None:
            self._config = self._load_json(self.config_file, {})
        return self._config

    def _load_json(self, path: Path, default: Any = None) -> Any:
        """Load JSON from file."""
        try:
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
        return default if default is not None else {}

    def save_settings(self, settings: Dict[str, Any]) -> bool:
        """Save settings to file."""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2)
            self._settings = settings
            return True
        except IOError:
            return False

    def get_projects(self) -> list:
        """Get list of project directories."""
        projects = []
        if self.projects_dir.exists():
            for item in self.projects_dir.iterdir():
                if item.is_dir():
                    projects.append(item)
        return sorted(projects, key=lambda x: x.stat().st_mtime, reverse=True)

    def get_stats_cache(self) -> Dict[str, Any]:
        """Load stats cache."""
        return self._load_json(self.stats_cache_file, {})

    def get_installed_plugins(self) -> Dict[str, Any]:
        """Load installed plugins."""
        plugins_file = self.plugins_dir / "installed_plugins.json"
        return self._load_json(plugins_file, {"plugins": {}})

    def get_claude_desktop_mcp_config(self) -> Dict[str, Any]:
        """Load Claude Desktop MCP configuration."""
        return self._load_json(self.claude_desktop_config, {"mcpServers": {}})
