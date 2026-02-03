"""
Agents panel for Claude Code Manager.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QListWidget, QListWidgetItem,
    QTextEdit, QLabel, QLineEdit, QPushButton, QGroupBox, QComboBox,
    QDoubleSpinBox, QPlainTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QMenu, QAction, QDialog, QFormLayout,
    QDialogButtonBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from datetime import datetime

from core.agent_manager import AgentManager
from core.models import Agent, AgentRun


class AgentWorker(QThread):
    """Worker thread for running agents."""
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, agent_manager: AgentManager, agent: Agent, prompt: str):
        super().__init__()
        self.agent_manager = agent_manager
        self.agent = agent
        self.prompt = prompt

    def run(self):
        """Run the agent."""
        try:
            run = self.agent_manager.run_agent(
                self.agent,
                self.prompt,
                background=False
            )
            self.finished.emit(run)
        except Exception as e:
            self.error.emit(str(e))


class AgentsPanel(QWidget):
    """Panel for managing custom agents."""

    def __init__(self, agent_manager: AgentManager):
        super().__init__()
        self.agent_manager = agent_manager
        self.current_agent = None
        self.worker = None

        self.setup_ui()
        self.refresh()

    def setup_ui(self):
        """Setup the user interface."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Create splitter
        splitter = QSplitter(Qt.Horizontal)

        # Left panel - Agent list
        left_panel = self.create_agent_list()
        splitter.addWidget(left_panel)

        # Middle panel - Agent editor/runner
        middle_panel = self.create_agent_editor()
        splitter.addWidget(middle_panel)

        # Right panel - Execution history
        right_panel = self.create_history_panel()
        splitter.addWidget(right_panel)

        splitter.setSizes([250, 450, 300])

        layout.addWidget(splitter)

    def create_agent_list(self) -> QWidget:
        """Create the agent list panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header_layout = QHBoxLayout()
        header = QLabel("Agents")
        header.setStyleSheet("font-size: 14px; font-weight: bold;")
        header_layout.addWidget(header)

        add_btn = QPushButton("+")
        add_btn.setFixedWidth(30)
        add_btn.clicked.connect(self.create_new_agent)
        header_layout.addWidget(add_btn)

        layout.addLayout(header_layout)

        # Agent list
        self.agent_list = QListWidget()
        self.agent_list.itemClicked.connect(self.on_agent_selected)
        self.agent_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.agent_list.customContextMenuRequested.connect(self.show_agent_context_menu)
        layout.addWidget(self.agent_list)

        # Templates section
        templates_group = QGroupBox("Templates")
        templates_layout = QVBoxLayout(templates_group)

        self.template_combo = QComboBox()
        templates_layout.addWidget(self.template_combo)

        use_template_btn = QPushButton("Create from Template")
        use_template_btn.clicked.connect(self.create_from_template)
        templates_layout.addWidget(use_template_btn)

        layout.addWidget(templates_group)

        return panel

    def create_agent_editor(self) -> QWidget:
        """Create the agent editor panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # Agent details group
        details_group = QGroupBox("Agent Configuration")
        details_layout = QFormLayout(details_group)

        self.name_input = QLineEdit()
        details_layout.addRow("Name:", self.name_input)

        self.description_input = QLineEdit()
        details_layout.addRow("Description:", self.description_input)

        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "claude-opus-4-5-20251101",
            "claude-sonnet-4-20250514",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022"
        ])
        details_layout.addRow("Model:", self.model_combo)

        self.temp_spinbox = QDoubleSpinBox()
        self.temp_spinbox.setRange(0.0, 2.0)
        self.temp_spinbox.setSingleStep(0.1)
        self.temp_spinbox.setValue(1.0)
        details_layout.addRow("Temperature:", self.temp_spinbox)

        layout.addWidget(details_group)

        # System prompt
        prompt_group = QGroupBox("System Prompt")
        prompt_layout = QVBoxLayout(prompt_group)

        self.system_prompt_edit = QPlainTextEdit()
        self.system_prompt_edit.setFont(QFont("Consolas", 10))
        self.system_prompt_edit.setPlaceholderText("Enter the system prompt for this agent...")
        prompt_layout.addWidget(self.system_prompt_edit)

        layout.addWidget(prompt_group)

        # Save button
        save_layout = QHBoxLayout()
        save_layout.addStretch()

        self.save_btn = QPushButton("Save Agent")
        self.save_btn.clicked.connect(self.save_agent)
        save_layout.addWidget(self.save_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setProperty("danger", True)
        self.delete_btn.clicked.connect(self.delete_agent)
        save_layout.addWidget(self.delete_btn)

        layout.addLayout(save_layout)

        # Run agent section
        run_group = QGroupBox("Run Agent")
        run_layout = QVBoxLayout(run_group)

        self.prompt_input = QPlainTextEdit()
        self.prompt_input.setMaximumHeight(100)
        self.prompt_input.setPlaceholderText("Enter your prompt here...")
        run_layout.addWidget(self.prompt_input)

        run_btn_layout = QHBoxLayout()
        self.run_btn = QPushButton("Run Agent")
        self.run_btn.clicked.connect(self.run_agent)
        run_btn_layout.addWidget(self.run_btn)

        self.run_bg_btn = QPushButton("Run in Background")
        self.run_bg_btn.clicked.connect(lambda: self.run_agent(background=True))
        run_btn_layout.addWidget(self.run_bg_btn)

        run_layout.addLayout(run_btn_layout)

        # Response display
        self.response_edit = QTextEdit()
        self.response_edit.setReadOnly(True)
        self.response_edit.setFont(QFont("Consolas", 10))
        run_layout.addWidget(self.response_edit)

        layout.addWidget(run_group)

        return panel

    def create_history_panel(self) -> QWidget:
        """Create the execution history panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QLabel("Execution History")
        header.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(header)

        # History table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels(["Agent", "Status", "Started", "Duration"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.itemDoubleClicked.connect(self.show_run_details)
        layout.addWidget(self.history_table)

        # Stats
        self.stats_label = QLabel()
        layout.addWidget(self.stats_label)

        return panel

    def refresh(self):
        """Refresh the agent list."""
        self.agent_list.clear()

        # Load agents
        agents = self.agent_manager.get_agents(force_refresh=True)
        for agent in agents:
            item = QListWidgetItem(agent.name)
            item.setData(Qt.UserRole, agent)
            item.setToolTip(agent.description)
            self.agent_list.addItem(item)

        # Load templates
        self.template_combo.clear()
        templates = self.agent_manager.get_default_agents()
        for template in templates:
            self.template_combo.addItem(template.name, template)

        # Load history
        self.refresh_history()

    def refresh_history(self):
        """Refresh execution history."""
        runs = self.agent_manager.get_runs(force_refresh=True)

        self.history_table.setRowCount(len(runs))

        for i, run in enumerate(runs):
            self.history_table.setItem(i, 0, QTableWidgetItem(run.agent_name))

            status_item = QTableWidgetItem(run.status)
            if run.status == "completed":
                status_item.setForeground(Qt.green)
            elif run.status == "failed":
                status_item.setForeground(Qt.red)
            self.history_table.setItem(i, 1, status_item)

            self.history_table.setItem(i, 2, QTableWidgetItem(
                run.started.strftime("%Y-%m-%d %H:%M")
            ))

            if run.completed:
                duration = (run.completed - run.started).total_seconds()
                self.history_table.setItem(i, 3, QTableWidgetItem(f"{duration:.1f}s"))
            else:
                self.history_table.setItem(i, 3, QTableWidgetItem("-"))

    def on_agent_selected(self, item: QListWidgetItem):
        """Handle agent selection."""
        agent = item.data(Qt.UserRole)
        if agent:
            self.current_agent = agent
            self.name_input.setText(agent.name)
            self.description_input.setText(agent.description)
            self.system_prompt_edit.setPlainText(agent.system_prompt)

            # Set model
            index = self.model_combo.findText(agent.model)
            if index >= 0:
                self.model_combo.setCurrentIndex(index)

            self.temp_spinbox.setValue(agent.temperature)

            # Update stats
            stats = self.agent_manager.get_agent_stats(agent.name)
            self.stats_label.setText(
                f"Runs: {stats['total_runs']} | "
                f"Success: {stats['successful_runs']} | "
                f"Failed: {stats['failed_runs']}"
            )

    def create_new_agent(self):
        """Create a new agent."""
        self.current_agent = None
        self.name_input.clear()
        self.description_input.clear()
        self.system_prompt_edit.clear()
        self.model_combo.setCurrentIndex(0)
        self.temp_spinbox.setValue(1.0)
        self.name_input.setFocus()

    def create_from_template(self):
        """Create agent from template."""
        template = self.template_combo.currentData()
        if template:
            self.current_agent = None
            self.name_input.setText(template.name)
            self.description_input.setText(template.description)
            self.system_prompt_edit.setPlainText(template.system_prompt)

            index = self.model_combo.findText(template.model)
            if index >= 0:
                self.model_combo.setCurrentIndex(index)

            self.temp_spinbox.setValue(template.temperature)

    def save_agent(self):
        """Save the current agent."""
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Agent name is required")
            return

        agent = Agent(
            name=name,
            description=self.description_input.text().strip(),
            system_prompt=self.system_prompt_edit.toPlainText().strip(),
            model=self.model_combo.currentText(),
            temperature=self.temp_spinbox.value()
        )

        if self.current_agent and self.current_agent.name == name:
            # Update existing
            agent.created = self.current_agent.created
            agent.run_count = self.current_agent.run_count
            agent.last_used = self.current_agent.last_used

            if self.agent_manager.update_agent(name, agent):
                QMessageBox.information(self, "Success", "Agent updated successfully")
                self.refresh()
            else:
                QMessageBox.warning(self, "Error", "Failed to update agent")
        else:
            # Create new
            if self.agent_manager.create_agent(agent):
                QMessageBox.information(self, "Success", "Agent created successfully")
                self.refresh()
            else:
                QMessageBox.warning(self, "Error", "Agent with this name already exists")

    def delete_agent(self):
        """Delete the current agent."""
        if not self.current_agent:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete agent '{self.current_agent.name}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.agent_manager.delete_agent(self.current_agent.name):
                self.create_new_agent()
                self.refresh()
            else:
                QMessageBox.warning(self, "Error", "Failed to delete agent")

    def run_agent(self, background: bool = False):
        """Run the selected agent."""
        if not self.current_agent:
            QMessageBox.warning(self, "Error", "Please select an agent first")
            return

        prompt = self.prompt_input.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, "Error", "Please enter a prompt")
            return

        self.run_btn.setEnabled(False)
        self.run_bg_btn.setEnabled(False)
        self.response_edit.setText("Running agent...")

        if background:
            self.agent_manager.run_agent(
                self.current_agent,
                prompt,
                callback=self.on_agent_finished,
                background=True
            )
            self.response_edit.setText("Agent running in background...")
            self.run_btn.setEnabled(True)
            self.run_bg_btn.setEnabled(True)
        else:
            self.worker = AgentWorker(self.agent_manager, self.current_agent, prompt)
            self.worker.finished.connect(self.on_agent_finished)
            self.worker.error.connect(self.on_agent_error)
            self.worker.start()

    def on_agent_finished(self, run: AgentRun):
        """Handle agent completion."""
        self.run_btn.setEnabled(True)
        self.run_bg_btn.setEnabled(True)

        if run.status == "completed":
            self.response_edit.setText(run.response)
        else:
            self.response_edit.setText(f"Error: {run.error or 'Unknown error'}")

        self.refresh_history()

    def on_agent_error(self, error: str):
        """Handle agent error."""
        self.run_btn.setEnabled(True)
        self.run_bg_btn.setEnabled(True)
        self.response_edit.setText(f"Error: {error}")

    def show_agent_context_menu(self, position):
        """Show context menu for agent list."""
        item = self.agent_list.itemAt(position)
        if not item:
            return

        menu = QMenu()

        duplicate_action = QAction("Duplicate", self)
        duplicate_action.triggered.connect(lambda: self.duplicate_agent(item.data(Qt.UserRole)))
        menu.addAction(duplicate_action)

        export_action = QAction("Export", self)
        export_action.triggered.connect(lambda: self.export_agent(item.data(Qt.UserRole)))
        menu.addAction(export_action)

        menu.exec_(self.agent_list.viewport().mapToGlobal(position))

    def duplicate_agent(self, agent: Agent):
        """Duplicate an agent."""
        self.current_agent = None
        self.name_input.setText(f"{agent.name} (Copy)")
        self.description_input.setText(agent.description)
        self.system_prompt_edit.setPlainText(agent.system_prompt)

        index = self.model_combo.findText(agent.model)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)

        self.temp_spinbox.setValue(agent.temperature)

    def export_agent(self, agent: Agent):
        """Export agent to file."""
        from PyQt5.QtWidgets import QFileDialog
        import json

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export Agent",
            f"{agent.name}.json",
            "JSON Files (*.json)"
        )

        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(agent.to_dict(), f, indent=2)
            QMessageBox.information(self, "Success", f"Agent exported to {filepath}")

    def show_run_details(self, item: QTableWidgetItem):
        """Show details of a run."""
        row = item.row()
        runs = self.agent_manager.get_runs()

        if 0 <= row < len(runs):
            run = runs[row]
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Run Details - {run.agent_name}")
            dialog.resize(600, 400)

            layout = QVBoxLayout(dialog)

            info = QLabel(
                f"Agent: {run.agent_name}\n"
                f"Status: {run.status}\n"
                f"Started: {run.started}\n"
                f"Completed: {run.completed or 'N/A'}"
            )
            layout.addWidget(info)

            prompt_group = QGroupBox("Prompt")
            prompt_layout = QVBoxLayout(prompt_group)
            prompt_text = QTextEdit()
            prompt_text.setReadOnly(True)
            prompt_text.setText(run.prompt)
            prompt_layout.addWidget(prompt_text)
            layout.addWidget(prompt_group)

            response_group = QGroupBox("Response")
            response_layout = QVBoxLayout(response_group)
            response_text = QTextEdit()
            response_text.setReadOnly(True)
            response_text.setText(run.response or run.error or "No response")
            response_layout.addWidget(response_text)
            layout.addWidget(response_group)

            dialog.exec_()
