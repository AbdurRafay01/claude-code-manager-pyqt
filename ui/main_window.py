"""
Main window for Claude Code Manager.
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QStatusBar, QLabel, QAction, QMenuBar, QMenu, QMessageBox,
    QFileDialog, QToolBar, QPushButton, QSplitter, QFrame
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon, QKeySequence

from core.config import Config
from core.session_manager import SessionManager
from core.agent_manager import AgentManager
from core.analytics_manager import AnalyticsManager
from core.mcp_manager import MCPManager
from core.checkpoint_manager import CheckpointManager
from core.claudemd_manager import ClaudeMdManager

from .panels.projects_panel import ProjectsPanel
from .panels.agents_panel import AgentsPanel
from .panels.analytics_panel import AnalyticsPanel
from .panels.mcp_panel import MCPPanel
from .panels.timeline_panel import TimelinePanel
from .panels.claudemd_panel import ClaudeMdPanel


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, config: Config):
        super().__init__()
        self.config = config

        # Initialize managers
        self.session_manager = SessionManager(config)
        self.agent_manager = AgentManager(config)
        self.analytics_manager = AnalyticsManager(config)
        self.mcp_manager = MCPManager(config)
        self.checkpoint_manager = CheckpointManager(config)
        self.claudemd_manager = ClaudeMdManager(config)

        self.setup_ui()
        self.setup_menu()
        self.setup_statusbar()

        # Refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.auto_refresh)
        self.refresh_timer.start(60000)  # Refresh every minute

    def setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle("Claude Code Manager")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = self.create_header()
        layout.addWidget(header)

        # Main tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)

        # Create panels
        self.projects_panel = ProjectsPanel(
            self.session_manager,
            self.checkpoint_manager
        )
        self.agents_panel = AgentsPanel(self.agent_manager)
        self.analytics_panel = AnalyticsPanel(self.analytics_manager)
        self.mcp_panel = MCPPanel(self.mcp_manager, self.config)
        self.timeline_panel = TimelinePanel(
            self.checkpoint_manager,
            self.session_manager
        )
        self.claudemd_panel = ClaudeMdPanel(self.claudemd_manager)

        # Add tabs
        self.tab_widget.addTab(self.projects_panel, "Projects & Sessions")
        self.tab_widget.addTab(self.agents_panel, "Agents")
        self.tab_widget.addTab(self.analytics_panel, "Analytics")
        self.tab_widget.addTab(self.mcp_panel, "MCP Servers")
        self.tab_widget.addTab(self.timeline_panel, "Timeline")
        self.tab_widget.addTab(self.claudemd_panel, "CLAUDE.md")

        layout.addWidget(self.tab_widget)

    def create_header(self) -> QWidget:
        """Create the header widget."""
        header = QFrame()
        header.setObjectName("header")
        header.setStyleSheet("""
            #header {
                background-color: #252526;
                border-bottom: 1px solid #3d3d3d;
            }
        """)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 8, 16, 8)

        # Logo/Title
        title = QLabel("Claude Code Manager")
        title.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #6495ed;
        """)
        layout.addWidget(title)

        layout.addStretch()

        # Quick actions
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setProperty("secondary", True)
        refresh_btn.clicked.connect(self.refresh_all)
        layout.addWidget(refresh_btn)

        settings_btn = QPushButton("Settings")
        settings_btn.setProperty("secondary", True)
        settings_btn.clicked.connect(self.show_settings)
        layout.addWidget(settings_btn)

        return header

    def setup_menu(self):
        """Setup the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        export_action = QAction("Export Analytics...", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(self.export_analytics)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View menu
        view_menu = menubar.addMenu("View")

        refresh_action = QAction("Refresh All", self)
        refresh_action.setShortcut(QKeySequence("F5"))
        refresh_action.triggered.connect(self.refresh_all)
        view_menu.addAction(refresh_action)

        view_menu.addSeparator()

        for i, (name, panel) in enumerate([
            ("Projects", self.projects_panel),
            ("Agents", self.agents_panel),
            ("Analytics", self.analytics_panel),
            ("MCP Servers", self.mcp_panel),
            ("Timeline", self.timeline_panel),
            ("CLAUDE.md", self.claudemd_panel),
        ]):
            action = QAction(name, self)
            action.setShortcut(QKeySequence(f"Ctrl+{i + 1}"))
            action.triggered.connect(lambda checked, idx=i: self.tab_widget.setCurrentIndex(idx))
            view_menu.addAction(action)

        # Tools menu
        tools_menu = menubar.addMenu("Tools")

        import_mcp_action = QAction("Import MCP from Claude Desktop", self)
        import_mcp_action.triggered.connect(self.import_mcp_from_desktop)
        tools_menu.addAction(import_mcp_action)

        scan_claude_md_action = QAction("Scan for CLAUDE.md files", self)
        scan_claude_md_action.triggered.connect(self.scan_claude_md)
        tools_menu.addAction(scan_claude_md_action)

        # Help menu
        help_menu = menubar.addMenu("Help")

        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def setup_statusbar(self):
        """Setup the status bar."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)

        # Stats label
        self.stats_label = QLabel()
        self.statusbar.addPermanentWidget(self.stats_label)

        self.update_stats_label()

    def update_stats_label(self):
        """Update the stats label in status bar."""
        try:
            summary = self.analytics_manager.get_summary_stats()
            self.stats_label.setText(
                f"Sessions: {summary['total_sessions']} | "
                f"Messages: {summary['total_messages']} | "
                f"Est. Cost: ${summary['total_cost']:.2f}"
            )
        except Exception:
            self.stats_label.setText("Stats unavailable")

    def refresh_all(self):
        """Refresh all panels."""
        self.statusbar.showMessage("Refreshing...", 2000)

        self.session_manager.clear_cache()
        self.projects_panel.refresh()
        self.agents_panel.refresh()
        self.analytics_panel.refresh()
        self.mcp_panel.refresh()
        self.timeline_panel.refresh()
        self.claudemd_panel.refresh()

        self.update_stats_label()
        self.statusbar.showMessage("Refreshed", 2000)

    def auto_refresh(self):
        """Auto-refresh callback."""
        self.update_stats_label()

    def export_analytics(self):
        """Export analytics to file."""
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export Analytics",
            "claude_analytics.json",
            "JSON Files (*.json);;CSV Files (*.csv)"
        )

        if filepath:
            format_type = 'csv' if filepath.endswith('.csv') else 'json'
            if self.analytics_manager.export_analytics(filepath, format_type):
                QMessageBox.information(self, "Success", f"Analytics exported to {filepath}")
            else:
                QMessageBox.warning(self, "Error", "Failed to export analytics")

    def import_mcp_from_desktop(self):
        """Import MCP servers from Claude Desktop."""
        imported = self.mcp_manager.import_from_claude_desktop()
        if imported:
            self.mcp_panel.refresh()
            QMessageBox.information(
                self,
                "Import Complete",
                f"Imported {len(imported)} MCP server(s) from Claude Desktop."
            )
        else:
            QMessageBox.information(
                self,
                "Import Complete",
                "No new MCP servers to import from Claude Desktop."
            )

    def scan_claude_md(self):
        """Scan for CLAUDE.md files."""
        self.claudemd_panel.refresh()
        self.tab_widget.setCurrentWidget(self.claudemd_panel)
        self.statusbar.showMessage("Scanning for CLAUDE.md files...", 3000)

    def show_settings(self):
        """Show settings dialog."""
        from .dialogs.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self.config, self)
        dialog.exec_()

    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About Claude Code Manager",
            """<h2>Claude Code Manager</h2>
            <p>Version 1.0.0</p>
            <p>A comprehensive GUI for managing Claude Code sessions, agents, and analytics.</p>
            <p>Features:</p>
            <ul>
                <li>Project & Session Management</li>
                <li>Custom AI Agents</li>
                <li>Usage Analytics Dashboard</li>
                <li>MCP Server Management</li>
                <li>Timeline & Checkpoints</li>
                <li>CLAUDE.md Management</li>
            </ul>
            """
        )

    def closeEvent(self, event):
        """Handle close event."""
        self.refresh_timer.stop()
        event.accept()
