"""
Projects and Sessions panel for Claude Code Manager.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTreeWidget, QTreeWidgetItem,
    QTextEdit, QLabel, QLineEdit, QPushButton, QGroupBox, QListWidget,
    QListWidgetItem, QMenu, QAction, QMessageBox, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from core.session_manager import SessionManager
from core.checkpoint_manager import CheckpointManager
from core.models import Project, Session


class ProjectsPanel(QWidget):
    """Panel for browsing projects and sessions."""

    session_selected = pyqtSignal(object)  # Emits Session object

    def __init__(self, session_manager: SessionManager, checkpoint_manager: CheckpointManager):
        super().__init__()
        self.session_manager = session_manager
        self.checkpoint_manager = checkpoint_manager

        self.setup_ui()
        self.refresh()

    def setup_ui(self):
        """Setup the user interface."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Create splitter
        splitter = QSplitter(Qt.Horizontal)

        # Left panel - Project browser
        left_panel = self.create_project_browser()
        splitter.addWidget(left_panel)

        # Right panel - Session details
        right_panel = self.create_session_details()
        splitter.addWidget(right_panel)

        # Set splitter sizes
        splitter.setSizes([400, 600])

        layout.addWidget(splitter)

    def create_project_browser(self) -> QWidget:
        """Create the project browser panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # Search box
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search projects and sessions...")
        self.search_input.textChanged.connect(self.on_search)
        search_layout.addWidget(self.search_input)

        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self.on_search)
        search_layout.addWidget(search_btn)

        layout.addLayout(search_layout)

        # Project tree
        self.project_tree = QTreeWidget()
        self.project_tree.setHeaderLabels(["Projects & Sessions"])
        self.project_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.project_tree.customContextMenuRequested.connect(self.show_context_menu)
        self.project_tree.itemClicked.connect(self.on_item_clicked)
        self.project_tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        layout.addWidget(self.project_tree)

        # Recent sessions
        recent_group = QGroupBox("Recent Sessions")
        recent_layout = QVBoxLayout(recent_group)

        self.recent_list = QListWidget()
        self.recent_list.itemClicked.connect(self.on_recent_clicked)
        recent_layout.addWidget(self.recent_list)

        layout.addWidget(recent_group)

        return panel

    def create_session_details(self) -> QWidget:
        """Create the session details panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QFrame()
        header_layout = QVBoxLayout(header)

        self.session_title = QLabel("Select a session")
        self.session_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_layout.addWidget(self.session_title)

        self.session_info = QLabel("")
        self.session_info.setStyleSheet("color: #888;")
        header_layout.addWidget(self.session_info)

        layout.addWidget(header)

        # Actions
        actions_layout = QHBoxLayout()

        self.resume_btn = QPushButton("Resume Session")
        self.resume_btn.clicked.connect(self.resume_session)
        self.resume_btn.setEnabled(False)
        actions_layout.addWidget(self.resume_btn)

        self.checkpoint_btn = QPushButton("Create Checkpoint")
        self.checkpoint_btn.clicked.connect(self.create_checkpoint)
        self.checkpoint_btn.setEnabled(False)
        actions_layout.addWidget(self.checkpoint_btn)

        actions_layout.addStretch()

        layout.addLayout(actions_layout)

        # Messages preview
        messages_group = QGroupBox("Session Preview")
        messages_layout = QVBoxLayout(messages_group)

        self.messages_view = QTextEdit()
        self.messages_view.setReadOnly(True)
        self.messages_view.setFont(QFont("Consolas", 10))
        messages_layout.addWidget(self.messages_view)

        layout.addWidget(messages_group)

        # Stats
        stats_group = QGroupBox("Session Statistics")
        stats_layout = QVBoxLayout(stats_group)

        self.stats_label = QLabel("No session selected")
        stats_layout.addWidget(self.stats_label)

        layout.addWidget(stats_group)

        return panel

    def refresh(self):
        """Refresh the project list."""
        self.project_tree.clear()
        self.recent_list.clear()

        projects = self.session_manager.get_projects(force_refresh=True)

        for project in projects:
            project_item = QTreeWidgetItem([project.name])
            project_item.setData(0, Qt.UserRole, project)

            for session in sorted(project.sessions, key=lambda s: s.modified, reverse=True):
                session_item = QTreeWidgetItem([
                    f"{session.summary[:50]}..." if len(session.summary) > 50 else session.summary
                ])
                session_item.setData(0, Qt.UserRole, session)
                session_item.setToolTip(0, f"Created: {session.created}\nMessages: {session.message_count}")
                project_item.addChild(session_item)

            self.project_tree.addTopLevelItem(project_item)

        # Populate recent sessions
        recent = self.session_manager.get_recent_sessions(limit=10)
        for item in recent:
            session = item['session']
            project = item['project']
            list_item = QListWidgetItem(f"{project.name}: {session.summary[:40]}...")
            list_item.setData(Qt.UserRole, (project, session))
            list_item.setToolTip(f"Modified: {session.modified}")
            self.recent_list.addItem(list_item)

    def on_search(self):
        """Handle search."""
        query = self.search_input.text().strip()
        if not query:
            self.refresh()
            return

        results = self.session_manager.search_sessions(query)

        self.project_tree.clear()

        for result in results:
            project = result['project']
            session = result['session']

            item = QTreeWidgetItem([
                f"{project.name}: {session.summary[:50]}..."
            ])
            item.setData(0, Qt.UserRole, session)
            self.project_tree.addTopLevelItem(item)

    def on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle item click."""
        data = item.data(0, Qt.UserRole)

        if isinstance(data, Session):
            self.show_session_details(data)
        elif isinstance(data, Project):
            self.session_title.setText(data.name)
            self.session_info.setText(f"{len(data.sessions)} sessions")
            self.messages_view.clear()
            self.resume_btn.setEnabled(False)
            self.checkpoint_btn.setEnabled(False)

    def on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle item double click."""
        data = item.data(0, Qt.UserRole)
        if isinstance(data, Session):
            self.resume_session()

    def on_recent_clicked(self, item: QListWidgetItem):
        """Handle recent session click."""
        data = item.data(Qt.UserRole)
        if data:
            project, session = data
            self.show_session_details(session)

    def show_session_details(self, session: Session):
        """Display session details."""
        self.current_session = session

        self.session_title.setText(session.summary or "Untitled Session")
        self.session_info.setText(
            f"ID: {session.session_id[:8]}... | "
            f"Messages: {session.message_count} | "
            f"Branch: {session.git_branch or 'N/A'}"
        )

        # Load messages
        messages = self.session_manager.get_session_messages(session.full_path)

        self.messages_view.clear()
        for msg in messages[:20]:  # Show first 20 messages
            role = "User" if msg.role == "user" else "Claude"
            content = msg.content[:500] + "..." if len(msg.content) > 500 else msg.content
            self.messages_view.append(f"**{role}:**\n{content}\n")

        if len(messages) > 20:
            self.messages_view.append(f"\n... and {len(messages) - 20} more messages")

        # Get stats
        stats = self.session_manager.get_session_stats(session)
        duration_mins = stats['duration_seconds'] / 60
        self.stats_label.setText(
            f"Total Messages: {stats['total_messages']}\n"
            f"User Messages: {stats['user_messages']}\n"
            f"Assistant Messages: {stats['assistant_messages']}\n"
            f"Duration: {duration_mins:.1f} minutes\n"
            f"Avg Response Length: {stats['avg_response_length']:.0f} chars"
        )

        self.resume_btn.setEnabled(True)
        self.checkpoint_btn.setEnabled(True)
        self.session_selected.emit(session)

    def show_context_menu(self, position):
        """Show context menu."""
        item = self.project_tree.itemAt(position)
        if not item:
            return

        data = item.data(0, Qt.UserRole)
        menu = QMenu()

        if isinstance(data, Session):
            resume_action = QAction("Resume Session", self)
            resume_action.triggered.connect(self.resume_session)
            menu.addAction(resume_action)

            checkpoint_action = QAction("Create Checkpoint", self)
            checkpoint_action.triggered.connect(self.create_checkpoint)
            menu.addAction(checkpoint_action)

            menu.addSeparator()

            copy_id_action = QAction("Copy Session ID", self)
            copy_id_action.triggered.connect(
                lambda: self.copy_to_clipboard(data.session_id)
            )
            menu.addAction(copy_id_action)

        elif isinstance(data, Project):
            open_folder_action = QAction("Open in Explorer", self)
            open_folder_action.triggered.connect(
                lambda: self.open_folder(str(data.path))
            )
            menu.addAction(open_folder_action)

        menu.exec_(self.project_tree.viewport().mapToGlobal(position))

    def resume_session(self):
        """Resume the selected session."""
        if not hasattr(self, 'current_session'):
            return

        import subprocess
        session = self.current_session

        # Build resume command
        cmd = f'claude --resume {session.session_id}'

        QMessageBox.information(
            self,
            "Resume Session",
            f"To resume this session, run:\n\n{cmd}\n\nIn your terminal."
        )

    def create_checkpoint(self):
        """Create a checkpoint for the current session."""
        if not hasattr(self, 'current_session'):
            return

        from ..dialogs.checkpoint_dialog import CheckpointDialog
        dialog = CheckpointDialog(self)

        if dialog.exec_():
            name, description = dialog.get_values()
            session = self.current_session

            # Get last message UUID
            messages = self.session_manager.get_session_messages(session.full_path)
            if messages:
                last_message_uuid = messages[-1].uuid

                checkpoint = self.checkpoint_manager.create_checkpoint(
                    session_id=session.session_id,
                    session_path=session.full_path,
                    message_uuid=last_message_uuid,
                    name=name,
                    description=description
                )

                QMessageBox.information(
                    self,
                    "Checkpoint Created",
                    f"Checkpoint '{name}' created successfully."
                )

    def copy_to_clipboard(self, text: str):
        """Copy text to clipboard."""
        from PyQt5.QtWidgets import QApplication
        QApplication.clipboard().setText(text)

    def open_folder(self, path: str):
        """Open folder in file explorer."""
        import os
        import subprocess
        if os.name == 'nt':
            subprocess.run(['explorer', path])
        else:
            subprocess.run(['xdg-open', path])
