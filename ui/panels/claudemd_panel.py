"""
CLAUDE.md management panel for Claude Code Manager.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QListWidget, QListWidgetItem,
    QTextEdit, QLabel, QLineEdit, QPushButton, QGroupBox, QComboBox,
    QPlainTextEdit, QMessageBox, QFileDialog, QMenu, QAction, QDialog,
    QFormLayout, QDialogButtonBox, QCheckBox
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QTextCharFormat, QSyntaxHighlighter, QColor
import re

from core.claudemd_manager import ClaudeMdManager


class MarkdownHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for Markdown."""

    def __init__(self, document):
        super().__init__(document)
        self.highlighting_rules = []

        # Heading
        heading_format = QTextCharFormat()
        heading_format.setForeground(QColor("#6495ed"))
        heading_format.setFontWeight(QFont.Bold)
        self.highlighting_rules.append((r'^#{1,6}\s.*$', heading_format))

        # Bold
        bold_format = QTextCharFormat()
        bold_format.setFontWeight(QFont.Bold)
        self.highlighting_rules.append((r'\*\*.*?\*\*', bold_format))
        self.highlighting_rules.append((r'__.*?__', bold_format))

        # Italic
        italic_format = QTextCharFormat()
        italic_format.setFontItalic(True)
        self.highlighting_rules.append((r'\*[^*]+\*', italic_format))
        self.highlighting_rules.append((r'_[^_]+_', italic_format))

        # Code inline
        code_format = QTextCharFormat()
        code_format.setForeground(QColor("#50c878"))
        code_format.setFontFamily("Consolas")
        self.highlighting_rules.append((r'`[^`]+`', code_format))

        # Links
        link_format = QTextCharFormat()
        link_format.setForeground(QColor("#ff6b6b"))
        self.highlighting_rules.append((r'\[.*?\]\(.*?\)', link_format))

        # List items
        list_format = QTextCharFormat()
        list_format.setForeground(QColor("#ffa500"))
        self.highlighting_rules.append((r'^\s*[-*+]\s', list_format))
        self.highlighting_rules.append((r'^\s*\d+\.\s', list_format))

        # Code block markers
        codeblock_format = QTextCharFormat()
        codeblock_format.setForeground(QColor("#888"))
        self.highlighting_rules.append((r'^```.*$', codeblock_format))

    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            for match in re.finditer(pattern, text, re.MULTILINE):
                self.setFormat(match.start(), match.end() - match.start(), format)


class ClaudeMdPanel(QWidget):
    """Panel for managing CLAUDE.md files."""

    def __init__(self, claudemd_manager: ClaudeMdManager):
        super().__init__()
        self.claudemd_manager = claudemd_manager
        self.current_file = None
        self.is_modified = False

        self.setup_ui()
        self.refresh()

    def setup_ui(self):
        """Setup the user interface."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Create splitter
        splitter = QSplitter(Qt.Horizontal)

        # Left panel - File browser
        left_panel = self.create_file_browser()
        splitter.addWidget(left_panel)

        # Right panel - Editor and preview
        right_panel = self.create_editor_panel()
        splitter.addWidget(right_panel)

        splitter.setSizes([300, 700])

        layout.addWidget(splitter)

    def create_file_browser(self) -> QWidget:
        """Create the file browser panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header_layout = QHBoxLayout()
        header = QLabel("CLAUDE.md Files")
        header.setStyleSheet("font-size: 14px; font-weight: bold;")
        header_layout.addWidget(header)

        scan_btn = QPushButton("Scan")
        scan_btn.setFixedWidth(60)
        scan_btn.clicked.connect(self.scan_files)
        header_layout.addWidget(scan_btn)

        layout.addLayout(header_layout)

        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search in CLAUDE.md files...")
        self.search_input.textChanged.connect(self.on_search)
        layout.addWidget(self.search_input)

        # File list
        self.file_list = QListWidget()
        self.file_list.itemClicked.connect(self.on_file_selected)
        self.file_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_list.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.file_list)

        # Templates
        template_group = QGroupBox("Create New")
        template_layout = QVBoxLayout(template_group)

        self.template_combo = QComboBox()
        template_layout.addWidget(self.template_combo)

        create_btn = QPushButton("Create CLAUDE.md")
        create_btn.clicked.connect(self.create_new_file)
        template_layout.addWidget(create_btn)

        layout.addWidget(template_group)

        # File info
        info_group = QGroupBox("File Info")
        info_layout = QVBoxLayout(info_group)

        self.info_label = QLabel("No file selected")
        self.info_label.setWordWrap(True)
        info_layout.addWidget(self.info_label)

        layout.addWidget(info_group)

        return panel

    def create_editor_panel(self) -> QWidget:
        """Create the editor panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar
        toolbar = QHBoxLayout()

        self.file_label = QLabel("No file open")
        self.file_label.setStyleSheet("font-weight: bold;")
        toolbar.addWidget(self.file_label)

        toolbar.addStretch()

        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_file)
        self.save_btn.setEnabled(False)
        toolbar.addWidget(self.save_btn)

        self.revert_btn = QPushButton("Revert")
        self.revert_btn.setProperty("secondary", True)
        self.revert_btn.clicked.connect(self.revert_file)
        self.revert_btn.setEnabled(False)
        toolbar.addWidget(self.revert_btn)

        layout.addLayout(toolbar)

        # Editor/Preview splitter
        editor_splitter = QSplitter(Qt.Horizontal)

        # Editor
        editor_widget = QWidget()
        editor_layout = QVBoxLayout(editor_widget)
        editor_layout.setContentsMargins(0, 0, 0, 0)

        editor_label = QLabel("Editor")
        editor_label.setStyleSheet("color: #888;")
        editor_layout.addWidget(editor_label)

        self.editor = QPlainTextEdit()
        self.editor.setFont(QFont("Consolas", 11))
        self.editor.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        self.editor.textChanged.connect(self.on_text_changed)

        # Add syntax highlighter
        self.highlighter = MarkdownHighlighter(self.editor.document())

        editor_layout.addWidget(self.editor)
        editor_splitter.addWidget(editor_widget)

        # Preview
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        preview_layout.setContentsMargins(0, 0, 0, 0)

        preview_label = QLabel("Preview")
        preview_label.setStyleSheet("color: #888;")
        preview_layout.addWidget(preview_label)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setFont(QFont("Segoe UI", 10))
        preview_layout.addWidget(self.preview)

        editor_splitter.addWidget(preview_widget)
        editor_splitter.setSizes([500, 500])

        layout.addWidget(editor_splitter)

        # Analysis
        analysis_group = QGroupBox("Analysis")
        analysis_layout = QHBoxLayout(analysis_group)

        self.analysis_label = QLabel("No file loaded")
        analysis_layout.addWidget(self.analysis_label)

        layout.addWidget(analysis_group)

        # Setup preview timer
        self.preview_timer = QTimer()
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self.update_preview)

        return panel

    def refresh(self):
        """Refresh the file list."""
        self.file_list.clear()

        # Load files
        files = self.claudemd_manager.find_claude_md_files()

        for file_info in files:
            item = QListWidgetItem(f"{file_info['project']} / {file_info['name']}")
            item.setData(Qt.UserRole, file_info)
            item.setToolTip(file_info['path'])

            if file_info['is_local']:
                item.setForeground(QColor("#ffa500"))

            self.file_list.addItem(item)

        # Load templates
        self.template_combo.clear()
        templates = self.claudemd_manager.get_available_templates()
        for template in templates:
            self.template_combo.addItem(template['name'], template)

    def scan_files(self):
        """Scan for CLAUDE.md files."""
        self.file_list.clear()

        # Show scanning message
        self.info_label.setText("Scanning for CLAUDE.md files...")

        QTimer.singleShot(100, self._do_scan)

    def _do_scan(self):
        """Perform the file scan."""
        files = self.claudemd_manager.find_claude_md_files()

        for file_info in files:
            item = QListWidgetItem(f"{file_info['project']} / {file_info['name']}")
            item.setData(Qt.UserRole, file_info)
            item.setToolTip(file_info['path'])

            if file_info['is_local']:
                item.setForeground(QColor("#ffa500"))

            self.file_list.addItem(item)

        self.info_label.setText(f"Found {len(files)} CLAUDE.md files")

    def on_search(self):
        """Handle search."""
        query = self.search_input.text().strip()
        if not query:
            self.refresh()
            return

        results = self.claudemd_manager.search_in_claude_md(query)

        self.file_list.clear()

        for result in results:
            match_text = result['matches'][0]['content'][:50] if result['matches'] else ""
            item = QListWidgetItem(f"{result['project']} / {result['name']}")
            item.setData(Qt.UserRole, result)
            item.setToolTip(f"Match: {match_text}...")
            self.file_list.addItem(item)

    def on_file_selected(self, item: QListWidgetItem):
        """Handle file selection."""
        if self.is_modified:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Discard them?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        file_info = item.data(Qt.UserRole)
        if file_info:
            self.load_file(file_info['path'])

            # Update info
            self.info_label.setText(
                f"Path: {file_info['path']}\n"
                f"Size: {file_info['size']} bytes\n"
                f"Modified: {file_info['modified'].strftime('%Y-%m-%d %H:%M')}"
            )

    def load_file(self, filepath: str):
        """Load a file into the editor."""
        content = self.claudemd_manager.read_claude_md(filepath)

        if content is not None:
            self.current_file = filepath
            self.editor.setPlainText(content)
            self.is_modified = False

            self.file_label.setText(filepath.split('/')[-1].split('\\')[-1])
            self.save_btn.setEnabled(True)
            self.revert_btn.setEnabled(False)

            self.update_analysis(content)
            self.update_preview()
        else:
            QMessageBox.warning(self, "Error", f"Could not read file: {filepath}")

    def on_text_changed(self):
        """Handle text changes."""
        if self.current_file:
            self.is_modified = True
            self.revert_btn.setEnabled(True)
            self.file_label.setText(f"{self.file_label.text().rstrip(' *')} *")

        # Debounce preview update
        self.preview_timer.start(500)

    def update_preview(self):
        """Update the markdown preview."""
        content = self.editor.toPlainText()
        html = self.markdown_to_html(content)
        self.preview.setHtml(html)

    def markdown_to_html(self, markdown: str) -> str:
        """Convert markdown to HTML (basic conversion)."""
        html = markdown

        # Escape HTML
        html = html.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        # Headings
        html = re.sub(r'^###### (.+)$', r'<h6>\1</h6>', html, flags=re.MULTILINE)
        html = re.sub(r'^##### (.+)$', r'<h5>\1</h5>', html, flags=re.MULTILINE)
        html = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

        # Bold and italic
        html = re.sub(r'\*\*\*(.+?)\*\*\*', r'<b><i>\1</i></b>', html)
        html = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', html)
        html = re.sub(r'\*(.+?)\*', r'<i>\1</i>', html)

        # Code
        html = re.sub(r'`([^`]+)`', r'<code style="background:#2d2d2d;padding:2px 4px;">\1</code>', html)

        # Links
        html = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2" style="color:#6495ed;">\1</a>', html)

        # List items
        html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        html = re.sub(r'^\* (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)

        # Paragraphs
        html = re.sub(r'\n\n', r'</p><p>', html)

        # Code blocks
        html = re.sub(
            r'```(\w*)\n(.*?)```',
            r'<pre style="background:#2d2d2d;padding:10px;border-radius:4px;overflow-x:auto;"><code>\2</code></pre>',
            html,
            flags=re.DOTALL
        )

        return f'<div style="color:#dcdcdc;font-family:Segoe UI;"><p>{html}</p></div>'

    def update_analysis(self, content: str):
        """Update the analysis section."""
        analysis = self.claudemd_manager.analyze_claude_md(content)

        sections = ', '.join(analysis['sections'][:5])
        if len(analysis['sections']) > 5:
            sections += f" (+{len(analysis['sections']) - 5} more)"

        self.analysis_label.setText(
            f"Lines: {analysis['total_lines']} | "
            f"Words: {analysis['word_count']} | "
            f"Headings: {len(analysis['headings'])} | "
            f"Sections: {sections}"
        )

    def save_file(self):
        """Save the current file."""
        if not self.current_file:
            return

        content = self.editor.toPlainText()

        if self.claudemd_manager.write_claude_md(self.current_file, content):
            self.is_modified = False
            self.revert_btn.setEnabled(False)
            self.file_label.setText(self.file_label.text().rstrip(' *'))
            QMessageBox.information(self, "Saved", "File saved successfully")
        else:
            QMessageBox.warning(self, "Error", "Failed to save file")

    def revert_file(self):
        """Revert to saved version."""
        if self.current_file:
            reply = QMessageBox.question(
                self,
                "Confirm Revert",
                "Discard all changes?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.load_file(self.current_file)

    def create_new_file(self):
        """Create a new CLAUDE.md file."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Project Folder"
        )

        if not folder:
            return

        template = self.template_combo.currentData()
        template_name = template['name'] if template else 'default'
        content = self.claudemd_manager.get_template(template_name)

        # Ask about local file
        reply = QMessageBox.question(
            self,
            "File Type",
            "Create as CLAUDE.local.md (gitignored)?",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
        )

        if reply == QMessageBox.Cancel:
            return

        local = reply == QMessageBox.Yes

        filepath = self.claudemd_manager.create_claude_md(folder, content, local)

        if filepath:
            QMessageBox.information(self, "Created", f"Created: {filepath}")
            self.refresh()
            self.load_file(filepath)
        else:
            QMessageBox.warning(self, "Error", "CLAUDE.md already exists in this folder")

    def show_context_menu(self, position):
        """Show context menu."""
        item = self.file_list.itemAt(position)
        if not item:
            return

        file_info = item.data(Qt.UserRole)
        menu = QMenu()

        open_action = QAction("Open in Editor", self)
        open_action.triggered.connect(lambda: self.load_file(file_info['path']))
        menu.addAction(open_action)

        open_folder_action = QAction("Open Folder", self)
        open_folder_action.triggered.connect(
            lambda: self.open_folder(file_info['project_path'])
        )
        menu.addAction(open_folder_action)

        menu.addSeparator()

        copy_path_action = QAction("Copy Path", self)
        copy_path_action.triggered.connect(
            lambda: self.copy_to_clipboard(file_info['path'])
        )
        menu.addAction(copy_path_action)

        menu.addSeparator()

        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(lambda: self.delete_file(file_info['path']))
        menu.addAction(delete_action)

        menu.exec_(self.file_list.viewport().mapToGlobal(position))

    def open_folder(self, path: str):
        """Open folder in file explorer."""
        import os
        import subprocess
        if os.name == 'nt':
            subprocess.run(['explorer', path])
        else:
            subprocess.run(['xdg-open', path])

    def copy_to_clipboard(self, text: str):
        """Copy text to clipboard."""
        from PyQt5.QtWidgets import QApplication
        QApplication.clipboard().setText(text)

    def delete_file(self, filepath: str):
        """Delete a CLAUDE.md file."""
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete this file?\n{filepath}\n\n"
            "(It will be renamed to .deleted)",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.claudemd_manager.delete_claude_md(filepath):
                if self.current_file == filepath:
                    self.current_file = None
                    self.editor.clear()
                    self.preview.clear()
                    self.file_label.setText("No file open")
                self.refresh()
            else:
                QMessageBox.warning(self, "Error", "Failed to delete file")
