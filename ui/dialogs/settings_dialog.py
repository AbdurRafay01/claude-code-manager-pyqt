"""
Settings dialog for Claude Code Manager.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit,
    QComboBox, QCheckBox, QPushButton, QGroupBox, QTabWidget, QWidget,
    QMessageBox, QDialogButtonBox
)
from PyQt5.QtCore import Qt

from core.config import Config


class SettingsDialog(QDialog):
    """Settings configuration dialog."""

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config

        self.setWindowTitle("Settings")
        self.resize(500, 400)

        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)

        # Tabs
        tabs = QTabWidget()

        # General tab
        general_tab = self.create_general_tab()
        tabs.addTab(general_tab, "General")

        # Paths tab
        paths_tab = self.create_paths_tab()
        tabs.addTab(paths_tab, "Paths")

        # About tab
        about_tab = self.create_about_tab()
        tabs.addTab(about_tab, "About")

        layout.addWidget(tabs)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.Apply).clicked.connect(self.apply_settings)
        layout.addWidget(buttons)

    def create_general_tab(self) -> QWidget:
        """Create the general settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Model settings
        model_group = QGroupBox("Default Model")
        model_layout = QFormLayout(model_group)

        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "claude-opus-4-5-20251101",
            "claude-sonnet-4-20250514",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022"
        ])
        model_layout.addRow("Model:", self.model_combo)

        layout.addWidget(model_group)

        # UI settings
        ui_group = QGroupBox("User Interface")
        ui_layout = QFormLayout(ui_group)

        self.auto_refresh_check = QCheckBox()
        self.auto_refresh_check.setChecked(True)
        ui_layout.addRow("Auto-refresh:", self.auto_refresh_check)

        self.show_tokens_check = QCheckBox()
        self.show_tokens_check.setChecked(True)
        ui_layout.addRow("Show token counts:", self.show_tokens_check)

        layout.addWidget(ui_group)

        layout.addStretch()

        return tab

    def create_paths_tab(self) -> QWidget:
        """Create the paths settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Claude paths
        paths_group = QGroupBox("Claude Code Paths")
        paths_layout = QFormLayout(paths_group)

        self.claude_dir_label = QLabel(str(self.config.claude_dir))
        self.claude_dir_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        paths_layout.addRow("Claude Directory:", self.claude_dir_label)

        self.projects_dir_label = QLabel(str(self.config.projects_dir))
        self.projects_dir_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        paths_layout.addRow("Projects Directory:", self.projects_dir_label)

        self.plugins_dir_label = QLabel(str(self.config.plugins_dir))
        self.plugins_dir_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        paths_layout.addRow("Plugins Directory:", self.plugins_dir_label)

        layout.addWidget(paths_group)

        # Desktop config
        desktop_group = QGroupBox("Claude Desktop")
        desktop_layout = QFormLayout(desktop_group)

        self.desktop_config_label = QLabel(str(self.config.claude_desktop_config))
        self.desktop_config_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        desktop_layout.addRow("Config File:", self.desktop_config_label)

        layout.addWidget(desktop_group)

        layout.addStretch()

        return tab

    def create_about_tab(self) -> QWidget:
        """Create the about tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        about_label = QLabel("""
        <h2>Claude Code Manager</h2>
        <p>Version 1.0.0</p>

        <p>A comprehensive GUI application for managing Claude Code sessions,
        custom agents, usage analytics, and more.</p>

        <h3>Features:</h3>
        <ul>
            <li>Project & Session Management</li>
            <li>Custom AI Agents</li>
            <li>Usage Analytics Dashboard</li>
            <li>MCP Server Management</li>
            <li>Timeline & Checkpoints</li>
            <li>CLAUDE.md File Management</li>
        </ul>

        <p>Built with PyQt5</p>
        """)
        about_label.setWordWrap(True)
        layout.addWidget(about_label)

        layout.addStretch()

        return tab

    def load_settings(self):
        """Load current settings."""
        settings = self.config.settings

        # Model
        model = settings.get('model', 'sonnet')
        model_map = {
            'opus': 'claude-opus-4-5-20251101',
            'sonnet': 'claude-sonnet-4-20250514'
        }
        full_model = model_map.get(model, model)
        index = self.model_combo.findText(full_model)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)

    def apply_settings(self):
        """Apply settings."""
        settings = self.config.settings.copy()

        # Get model short name
        model_text = self.model_combo.currentText()
        if 'opus' in model_text:
            settings['model'] = 'opus'
        elif 'sonnet' in model_text:
            settings['model'] = 'sonnet'
        elif 'haiku' in model_text:
            settings['model'] = 'haiku'

        if self.config.save_settings(settings):
            QMessageBox.information(self, "Success", "Settings saved")
        else:
            QMessageBox.warning(self, "Error", "Failed to save settings")

    def accept(self):
        """Accept and save settings."""
        self.apply_settings()
        super().accept()
