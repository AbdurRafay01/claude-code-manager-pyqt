"""
MCP Server panel for Claude Code Manager.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QListWidget, QListWidgetItem,
    QLabel, QLineEdit, QPushButton, QGroupBox, QFormLayout, QPlainTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QComboBox,
    QDialog, QDialogButtonBox, QMenu, QAction
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from core.mcp_manager import MCPManager
from core.config import Config
from core.models import MCPServer


class MCPPanel(QWidget):
    """Panel for managing MCP servers."""

    def __init__(self, mcp_manager: MCPManager, config: Config):
        super().__init__()
        self.mcp_manager = mcp_manager
        self.config = config
        self.current_server = None

        self.setup_ui()
        self.refresh()

    def setup_ui(self):
        """Setup the user interface."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Create splitter
        splitter = QSplitter(Qt.Horizontal)

        # Left panel - Server list
        left_panel = self.create_server_list()
        splitter.addWidget(left_panel)

        # Right panel - Server details
        right_panel = self.create_server_details()
        splitter.addWidget(right_panel)

        splitter.setSizes([300, 700])

        layout.addWidget(splitter)

    def create_server_list(self) -> QWidget:
        """Create the server list panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header_layout = QHBoxLayout()
        header = QLabel("MCP Servers")
        header.setStyleSheet("font-size: 14px; font-weight: bold;")
        header_layout.addWidget(header)

        add_btn = QPushButton("+")
        add_btn.setFixedWidth(30)
        add_btn.clicked.connect(self.create_new_server)
        header_layout.addWidget(add_btn)

        layout.addLayout(header_layout)

        # Server list
        self.server_list = QListWidget()
        self.server_list.itemClicked.connect(self.on_server_selected)
        self.server_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.server_list.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.server_list)

        # Import/Template buttons
        import_group = QGroupBox("Quick Add")
        import_layout = QVBoxLayout(import_group)

        import_desktop_btn = QPushButton("Import from Claude Desktop")
        import_desktop_btn.clicked.connect(self.import_from_desktop)
        import_layout.addWidget(import_desktop_btn)

        self.template_combo = QComboBox()
        import_layout.addWidget(self.template_combo)

        add_template_btn = QPushButton("Add from Template")
        add_template_btn.clicked.connect(self.add_from_template)
        import_layout.addWidget(add_template_btn)

        layout.addWidget(import_group)

        # Plugin MCP servers
        plugin_group = QGroupBox("Plugin MCP Servers")
        plugin_layout = QVBoxLayout(plugin_group)

        self.plugin_list = QListWidget()
        self.plugin_list.setMaximumHeight(150)
        plugin_layout.addWidget(self.plugin_list)

        layout.addWidget(plugin_group)

        return panel

    def create_server_details(self) -> QWidget:
        """Create the server details panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # Server configuration
        config_group = QGroupBox("Server Configuration")
        config_layout = QFormLayout(config_group)

        self.name_input = QLineEdit()
        config_layout.addRow("Name:", self.name_input)

        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("e.g., npx, uvx, node")
        config_layout.addRow("Command:", self.command_input)

        self.args_input = QLineEdit()
        self.args_input.setPlaceholderText("e.g., -y @modelcontextprotocol/server-filesystem /path")
        config_layout.addRow("Arguments:", self.args_input)

        layout.addWidget(config_group)

        # Environment variables
        env_group = QGroupBox("Environment Variables")
        env_layout = QVBoxLayout(env_group)

        self.env_table = QTableWidget()
        self.env_table.setColumnCount(2)
        self.env_table.setHorizontalHeaderLabels(["Variable", "Value"])
        self.env_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        env_layout.addWidget(self.env_table)

        env_btn_layout = QHBoxLayout()
        add_env_btn = QPushButton("Add Variable")
        add_env_btn.clicked.connect(self.add_env_variable)
        env_btn_layout.addWidget(add_env_btn)

        remove_env_btn = QPushButton("Remove Selected")
        remove_env_btn.clicked.connect(self.remove_env_variable)
        env_btn_layout.addWidget(remove_env_btn)

        env_layout.addLayout(env_btn_layout)
        layout.addWidget(env_group)

        # Actions
        actions_layout = QHBoxLayout()

        self.test_btn = QPushButton("Test Connection")
        self.test_btn.clicked.connect(self.test_connection)
        actions_layout.addWidget(self.test_btn)

        self.save_btn = QPushButton("Save Server")
        self.save_btn.clicked.connect(self.save_server)
        actions_layout.addWidget(self.save_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setProperty("danger", True)
        self.delete_btn.clicked.connect(self.delete_server)
        actions_layout.addWidget(self.delete_btn)

        actions_layout.addStretch()

        layout.addLayout(actions_layout)

        # Test results
        results_group = QGroupBox("Connection Test Results")
        results_layout = QVBoxLayout(results_group)

        self.results_text = QPlainTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setFont(QFont("Consolas", 10))
        self.results_text.setMaximumHeight(150)
        results_layout.addWidget(self.results_text)

        layout.addWidget(results_group)

        # Configuration preview
        preview_group = QGroupBox("Configuration Preview (JSON)")
        preview_layout = QVBoxLayout(preview_group)

        self.preview_text = QPlainTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setFont(QFont("Consolas", 10))
        preview_layout.addWidget(self.preview_text)

        layout.addWidget(preview_group)

        return panel

    def refresh(self):
        """Refresh the server list."""
        self.server_list.clear()

        # Load servers
        servers = self.mcp_manager.get_servers(force_refresh=True)
        for server in servers:
            item = QListWidgetItem(server.name)
            item.setData(Qt.UserRole, server)
            item.setToolTip(f"Command: {server.command}")
            self.server_list.addItem(item)

        # Load templates
        self.template_combo.clear()
        templates = self.mcp_manager.get_available_mcp_templates()
        for template in templates:
            self.template_combo.addItem(template['name'], template)

        # Load plugin MCP servers
        self.plugin_list.clear()
        plugins = self.mcp_manager.discover_plugin_mcp_servers()
        for plugin in plugins:
            item = QListWidgetItem(f"{plugin['plugin']}")
            item.setToolTip(plugin['path'])
            item.setData(Qt.UserRole, plugin)
            self.plugin_list.addItem(item)

        self.update_preview()

    def on_server_selected(self, item: QListWidgetItem):
        """Handle server selection."""
        server = item.data(Qt.UserRole)
        if server:
            self.current_server = server
            self.name_input.setText(server.name)
            self.command_input.setText(server.command)
            self.args_input.setText(' '.join(server.args))

            # Load environment variables
            self.env_table.setRowCount(len(server.env))
            for i, (key, value) in enumerate(server.env.items()):
                self.env_table.setItem(i, 0, QTableWidgetItem(key))
                self.env_table.setItem(i, 1, QTableWidgetItem(value))

            self.update_preview()

    def create_new_server(self):
        """Create a new server."""
        self.current_server = None
        self.name_input.clear()
        self.command_input.clear()
        self.args_input.clear()
        self.env_table.setRowCount(0)
        self.results_text.clear()
        self.update_preview()

    def add_from_template(self):
        """Add server from template."""
        template = self.template_combo.currentData()
        if template:
            self.current_server = None
            self.name_input.setText(template['name'])
            self.command_input.setText(template['command'])
            self.args_input.setText(' '.join(template['args']))

            env = template.get('env', {})
            self.env_table.setRowCount(len(env))
            for i, (key, value) in enumerate(env.items()):
                self.env_table.setItem(i, 0, QTableWidgetItem(key))
                self.env_table.setItem(i, 1, QTableWidgetItem(value))

            self.update_preview()

    def import_from_desktop(self):
        """Import servers from Claude Desktop."""
        imported = self.mcp_manager.import_from_claude_desktop()
        if imported:
            self.refresh()
            QMessageBox.information(
                self,
                "Import Complete",
                f"Imported {len(imported)} server(s) from Claude Desktop."
            )
        else:
            QMessageBox.information(
                self,
                "Import Complete",
                "No new servers to import."
            )

    def add_env_variable(self):
        """Add an environment variable row."""
        row = self.env_table.rowCount()
        self.env_table.insertRow(row)
        self.env_table.setItem(row, 0, QTableWidgetItem(""))
        self.env_table.setItem(row, 1, QTableWidgetItem(""))

    def remove_env_variable(self):
        """Remove selected environment variable."""
        row = self.env_table.currentRow()
        if row >= 0:
            self.env_table.removeRow(row)

    def save_server(self):
        """Save the current server."""
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Server name is required")
            return

        command = self.command_input.text().strip()
        if not command:
            QMessageBox.warning(self, "Error", "Command is required")
            return

        args = self.args_input.text().strip().split() if self.args_input.text().strip() else []

        # Get environment variables
        env = {}
        for row in range(self.env_table.rowCount()):
            key_item = self.env_table.item(row, 0)
            value_item = self.env_table.item(row, 1)
            if key_item and value_item:
                key = key_item.text().strip()
                value = value_item.text().strip()
                if key:
                    env[key] = value

        server = MCPServer(
            name=name,
            command=command,
            args=args,
            env=env
        )

        if self.current_server and self.current_server.name == name:
            # Update existing
            if self.mcp_manager.update_server(name, server):
                QMessageBox.information(self, "Success", "Server updated successfully")
                self.refresh()
            else:
                QMessageBox.warning(self, "Error", "Failed to update server")
        else:
            # Create new
            if self.mcp_manager.add_server(server):
                QMessageBox.information(self, "Success", "Server added successfully")
                self.refresh()
            else:
                QMessageBox.warning(self, "Error", "Server with this name already exists")

    def delete_server(self):
        """Delete the current server."""
        if not self.current_server:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete server '{self.current_server.name}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.mcp_manager.delete_server(self.current_server.name):
                self.create_new_server()
                self.refresh()
            else:
                QMessageBox.warning(self, "Error", "Failed to delete server")

    def test_connection(self):
        """Test the server connection."""
        name = self.name_input.text().strip()
        command = self.command_input.text().strip()
        args = self.args_input.text().strip().split() if self.args_input.text().strip() else []

        # Get environment variables
        env = {}
        for row in range(self.env_table.rowCount()):
            key_item = self.env_table.item(row, 0)
            value_item = self.env_table.item(row, 1)
            if key_item and value_item:
                key = key_item.text().strip()
                value = value_item.text().strip()
                if key:
                    env[key] = value

        server = MCPServer(name=name, command=command, args=args, env=env)

        self.results_text.setPlainText("Testing connection...")
        self.test_btn.setEnabled(False)

        # Run test
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, lambda: self._do_test(server))

    def _do_test(self, server: MCPServer):
        """Perform the connection test."""
        result = self.mcp_manager.test_server_connection(server)

        if result['success']:
            self.results_text.setPlainText(f"Success: {result['message']}")
        else:
            text = f"Failed: {result['message']}"
            if result.get('details', {}).get('stderr'):
                text += f"\n\nStderr:\n{result['details']['stderr']}"
            self.results_text.setPlainText(text)

        self.test_btn.setEnabled(True)

    def update_preview(self):
        """Update the configuration preview."""
        import json

        name = self.name_input.text().strip() or "server-name"
        command = self.command_input.text().strip() or "command"
        args = self.args_input.text().strip().split() if self.args_input.text().strip() else []

        env = {}
        for row in range(self.env_table.rowCount()):
            key_item = self.env_table.item(row, 0)
            value_item = self.env_table.item(row, 1)
            if key_item and value_item:
                key = key_item.text().strip()
                value = value_item.text().strip()
                if key:
                    env[key] = value

        config = {
            "mcpServers": {
                name: {
                    "command": command,
                    "args": args
                }
            }
        }

        if env:
            config["mcpServers"][name]["env"] = env

        self.preview_text.setPlainText(json.dumps(config, indent=2))

    def show_context_menu(self, position):
        """Show context menu."""
        item = self.server_list.itemAt(position)
        if not item:
            return

        menu = QMenu()

        duplicate_action = QAction("Duplicate", self)
        duplicate_action.triggered.connect(lambda: self.duplicate_server(item.data(Qt.UserRole)))
        menu.addAction(duplicate_action)

        menu.exec_(self.server_list.viewport().mapToGlobal(position))

    def duplicate_server(self, server: MCPServer):
        """Duplicate a server."""
        self.current_server = None
        self.name_input.setText(f"{server.name}-copy")
        self.command_input.setText(server.command)
        self.args_input.setText(' '.join(server.args))

        self.env_table.setRowCount(len(server.env))
        for i, (key, value) in enumerate(server.env.items()):
            self.env_table.setItem(i, 0, QTableWidgetItem(key))
            self.env_table.setItem(i, 1, QTableWidgetItem(value))

        self.update_preview()
