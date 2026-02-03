"""
Timeline panel for Claude Code Manager.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTreeWidget, QTreeWidgetItem,
    QTextEdit, QLabel, QLineEdit, QPushButton, QGroupBox, QComboBox,
    QListWidget, QListWidgetItem, QMessageBox, QDialog, QFormLayout,
    QDialogButtonBox, QPlainTextEdit
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
import uuid

from core.checkpoint_manager import CheckpointManager
from core.session_manager import SessionManager
from core.models import Checkpoint


class TimelinePanel(QWidget):
    """Panel for managing session timeline and checkpoints."""

    def __init__(self, checkpoint_manager: CheckpointManager, session_manager: SessionManager):
        super().__init__()
        self.checkpoint_manager = checkpoint_manager
        self.session_manager = session_manager
        self.current_session = None
        self.current_checkpoint = None

        self.setup_ui()
        self.refresh()

    def setup_ui(self):
        """Setup the user interface."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Create splitter
        splitter = QSplitter(Qt.Horizontal)

        # Left panel - Session selector and timeline
        left_panel = self.create_timeline_browser()
        splitter.addWidget(left_panel)

        # Right panel - Checkpoint details
        right_panel = self.create_checkpoint_details()
        splitter.addWidget(right_panel)

        splitter.setSizes([400, 600])

        layout.addWidget(splitter)

    def create_timeline_browser(self) -> QWidget:
        """Create the timeline browser panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # Session selector
        session_group = QGroupBox("Select Session")
        session_layout = QVBoxLayout(session_group)

        self.session_combo = QComboBox()
        self.session_combo.currentIndexChanged.connect(self.on_session_changed)
        session_layout.addWidget(self.session_combo)

        layout.addWidget(session_group)

        # Timeline tree
        timeline_group = QGroupBox("Checkpoint Timeline")
        timeline_layout = QVBoxLayout(timeline_group)

        self.timeline_tree = QTreeWidget()
        self.timeline_tree.setHeaderLabels(["Checkpoint", "Time"])
        self.timeline_tree.itemClicked.connect(self.on_checkpoint_selected)
        timeline_layout.addWidget(self.timeline_tree)

        # Timeline actions
        actions_layout = QHBoxLayout()

        self.create_btn = QPushButton("Create Checkpoint")
        self.create_btn.clicked.connect(self.create_checkpoint)
        actions_layout.addWidget(self.create_btn)

        timeline_layout.addLayout(actions_layout)

        layout.addWidget(timeline_group)

        # Branch list
        branch_group = QGroupBox("Branches")
        branch_layout = QVBoxLayout(branch_group)

        self.branch_list = QListWidget()
        self.branch_list.itemClicked.connect(self.on_branch_selected)
        branch_layout.addWidget(self.branch_list)

        layout.addWidget(branch_group)

        return panel

    def create_checkpoint_details(self) -> QWidget:
        """Create the checkpoint details panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # Checkpoint info
        info_group = QGroupBox("Checkpoint Details")
        info_layout = QFormLayout(info_group)

        self.name_label = QLabel("-")
        info_layout.addRow("Name:", self.name_label)

        self.desc_label = QLabel("-")
        info_layout.addRow("Description:", self.desc_label)

        self.time_label = QLabel("-")
        info_layout.addRow("Created:", self.time_label)

        self.branch_label = QLabel("-")
        info_layout.addRow("Branch:", self.branch_label)

        layout.addWidget(info_group)

        # Actions
        actions_group = QGroupBox("Actions")
        actions_layout = QVBoxLayout(actions_group)

        btn_layout = QHBoxLayout()

        self.restore_btn = QPushButton("Restore to This Checkpoint")
        self.restore_btn.clicked.connect(self.restore_checkpoint)
        self.restore_btn.setEnabled(False)
        btn_layout.addWidget(self.restore_btn)

        self.fork_btn = QPushButton("Fork New Session")
        self.fork_btn.clicked.connect(self.fork_session)
        self.fork_btn.setEnabled(False)
        btn_layout.addWidget(self.fork_btn)

        actions_layout.addLayout(btn_layout)

        btn_layout2 = QHBoxLayout()

        self.diff_btn = QPushButton("Compare with Another")
        self.diff_btn.clicked.connect(self.compare_checkpoints)
        self.diff_btn.setEnabled(False)
        btn_layout2.addWidget(self.diff_btn)

        self.delete_cp_btn = QPushButton("Delete Checkpoint")
        self.delete_cp_btn.setProperty("danger", True)
        self.delete_cp_btn.clicked.connect(self.delete_checkpoint)
        self.delete_cp_btn.setEnabled(False)
        btn_layout2.addWidget(self.delete_cp_btn)

        actions_layout.addLayout(btn_layout2)

        layout.addWidget(actions_group)

        # Messages preview
        preview_group = QGroupBox("Checkpoint Messages Preview")
        preview_layout = QVBoxLayout(preview_group)

        self.messages_view = QTextEdit()
        self.messages_view.setReadOnly(True)
        self.messages_view.setFont(QFont("Consolas", 10))
        preview_layout.addWidget(self.messages_view)

        layout.addWidget(preview_group)

        # Diff view
        diff_group = QGroupBox("Diff View")
        diff_layout = QVBoxLayout(diff_group)

        self.diff_view = QPlainTextEdit()
        self.diff_view.setReadOnly(True)
        self.diff_view.setFont(QFont("Consolas", 10))
        diff_layout.addWidget(self.diff_view)

        layout.addWidget(diff_group)

        return panel

    def refresh(self):
        """Refresh the panel data."""
        # Load sessions into combo
        self.session_combo.clear()
        self.session_combo.addItem("Select a session...", None)

        projects = self.session_manager.get_projects()
        for project in projects:
            for session in project.sessions:
                display_name = f"{project.name}: {session.summary[:30]}..."
                self.session_combo.addItem(display_name, session)

        self.refresh_timeline()

    def refresh_timeline(self):
        """Refresh the timeline tree."""
        self.timeline_tree.clear()
        self.branch_list.clear()

        if not self.current_session:
            return

        checkpoints = self.checkpoint_manager.get_checkpoints(self.current_session.session_id)

        # Build tree
        checkpoint_items = {}
        branches = set()

        for cp in sorted(checkpoints, key=lambda x: x.timestamp):
            item = QTreeWidgetItem([
                cp.name,
                cp.timestamp.strftime("%Y-%m-%d %H:%M")
            ])
            item.setData(0, Qt.UserRole, cp)

            if cp.branch_name:
                branches.add(cp.branch_name)
                item.setForeground(0, QColor("#6495ed"))

            if cp.parent_checkpoint_id and cp.parent_checkpoint_id in checkpoint_items:
                checkpoint_items[cp.parent_checkpoint_id].addChild(item)
            else:
                self.timeline_tree.addTopLevelItem(item)

            checkpoint_items[cp.checkpoint_id] = item

        self.timeline_tree.expandAll()

        # Update branch list
        for branch in branches:
            self.branch_list.addItem(branch)

    def on_session_changed(self, index: int):
        """Handle session selection change."""
        session = self.session_combo.currentData()
        self.current_session = session
        self.refresh_timeline()

    def on_checkpoint_selected(self, item: QTreeWidgetItem, column: int):
        """Handle checkpoint selection."""
        checkpoint = item.data(0, Qt.UserRole)
        if checkpoint:
            self.current_checkpoint = checkpoint
            self.show_checkpoint_details(checkpoint)

    def on_branch_selected(self, item: QListWidgetItem):
        """Handle branch selection."""
        branch_name = item.text()
        # Filter timeline to show only this branch
        for i in range(self.timeline_tree.topLevelItemCount()):
            top_item = self.timeline_tree.topLevelItem(i)
            self._filter_branch(top_item, branch_name)

    def _filter_branch(self, item: QTreeWidgetItem, branch_name: str):
        """Filter tree items by branch."""
        checkpoint = item.data(0, Qt.UserRole)
        if checkpoint:
            visible = checkpoint.branch_name == branch_name or not checkpoint.branch_name
            item.setHidden(not visible)

        for i in range(item.childCount()):
            self._filter_branch(item.child(i), branch_name)

    def show_checkpoint_details(self, checkpoint: Checkpoint):
        """Display checkpoint details."""
        self.name_label.setText(checkpoint.name)
        self.desc_label.setText(checkpoint.description or "No description")
        self.time_label.setText(checkpoint.timestamp.strftime("%Y-%m-%d %H:%M:%S"))
        self.branch_label.setText(checkpoint.branch_name or "main")

        # Enable actions
        self.restore_btn.setEnabled(True)
        self.fork_btn.setEnabled(True)
        self.diff_btn.setEnabled(True)
        self.delete_cp_btn.setEnabled(True)

        # Load messages
        messages = self.checkpoint_manager.get_checkpoint_messages(checkpoint.checkpoint_id)
        self.messages_view.clear()

        for msg in messages[-10:]:  # Last 10 messages
            message = msg.get('message', {})
            role = "User" if message.get('role') == 'user' else "Claude"
            content = message.get('content', '')
            if isinstance(content, str):
                content = content[:300] + "..." if len(content) > 300 else content
            self.messages_view.append(f"**{role}:**\n{content}\n")

    def create_checkpoint(self):
        """Create a new checkpoint."""
        if not self.current_session:
            QMessageBox.warning(self, "Error", "Please select a session first")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Create Checkpoint")
        dialog.resize(400, 200)

        layout = QVBoxLayout(dialog)

        form = QFormLayout()

        name_input = QLineEdit()
        form.addRow("Name:", name_input)

        desc_input = QLineEdit()
        form.addRow("Description:", desc_input)

        branch_input = QLineEdit()
        branch_input.setPlaceholderText("Optional branch name")
        form.addRow("Branch:", branch_input)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec_() == QDialog.Accepted:
            name = name_input.text().strip()
            if not name:
                QMessageBox.warning(self, "Error", "Checkpoint name is required")
                return

            # Get last message
            messages = self.session_manager.get_session_messages(self.current_session.full_path)
            if messages:
                last_uuid = messages[-1].uuid

                parent_id = self.current_checkpoint.checkpoint_id if self.current_checkpoint else None

                checkpoint = self.checkpoint_manager.create_checkpoint(
                    session_id=self.current_session.session_id,
                    session_path=self.current_session.full_path,
                    message_uuid=last_uuid,
                    name=name,
                    description=desc_input.text().strip(),
                    parent_checkpoint_id=parent_id,
                    branch_name=branch_input.text().strip() or None
                )

                QMessageBox.information(self, "Success", f"Checkpoint '{name}' created")
                self.refresh_timeline()

    def restore_checkpoint(self):
        """Restore to the selected checkpoint."""
        if not self.current_checkpoint or not self.current_session:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Restore",
            f"Are you sure you want to restore to checkpoint '{self.current_checkpoint.name}'?\n\n"
            "This will create a backup of the current session.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.checkpoint_manager.restore_checkpoint(
                self.current_checkpoint.checkpoint_id,
                self.current_session.full_path
            ):
                QMessageBox.information(
                    self,
                    "Restored",
                    f"Session restored to checkpoint '{self.current_checkpoint.name}'.\n"
                    "A backup has been created."
                )
            else:
                QMessageBox.warning(self, "Error", "Failed to restore checkpoint")

    def fork_session(self):
        """Fork a new session from checkpoint."""
        if not self.current_checkpoint or not self.current_session:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Fork Session")
        dialog.resize(300, 150)

        layout = QVBoxLayout(dialog)

        form = QFormLayout()

        branch_input = QLineEdit()
        branch_input.setText("fork")
        form.addRow("Branch Name:", branch_input)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec_() == QDialog.Accepted:
            branch_name = branch_input.text().strip() or "fork"
            new_session_id = str(uuid.uuid4())

            # Get project path from session
            from pathlib import Path
            project_path = Path(self.current_session.full_path).parent

            result = self.checkpoint_manager.fork_session(
                self.current_checkpoint.checkpoint_id,
                new_session_id,
                project_path,
                branch_name
            )

            if result:
                QMessageBox.information(
                    self,
                    "Forked",
                    f"New session created from checkpoint.\n"
                    f"Session ID: {new_session_id[:8]}...\n"
                    f"Branch: {branch_name}"
                )
                self.session_manager.clear_cache()
                self.refresh()
            else:
                QMessageBox.warning(self, "Error", "Failed to fork session")

    def compare_checkpoints(self):
        """Compare two checkpoints."""
        if not self.current_checkpoint:
            return

        checkpoints = self.checkpoint_manager.get_checkpoints(self.current_session.session_id)
        other_checkpoints = [c for c in checkpoints if c.checkpoint_id != self.current_checkpoint.checkpoint_id]

        if not other_checkpoints:
            QMessageBox.information(self, "Info", "No other checkpoints to compare with")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Compare Checkpoints")
        dialog.resize(300, 150)

        layout = QVBoxLayout(dialog)

        combo = QComboBox()
        for cp in other_checkpoints:
            combo.addItem(cp.name, cp)
        layout.addWidget(combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec_() == QDialog.Accepted:
            other = combo.currentData()
            if other:
                diff = self.checkpoint_manager.get_diff_between_checkpoints(
                    self.current_checkpoint.checkpoint_id,
                    other.checkpoint_id
                )

                self.diff_view.setPlainText('\n'.join(diff) if diff else "No differences found")

    def delete_checkpoint(self):
        """Delete the selected checkpoint."""
        if not self.current_checkpoint:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete checkpoint '{self.current_checkpoint.name}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.checkpoint_manager.delete_checkpoint(self.current_checkpoint.checkpoint_id):
                self.current_checkpoint = None
                self.refresh_timeline()
            else:
                QMessageBox.warning(self, "Error", "Failed to delete checkpoint")
