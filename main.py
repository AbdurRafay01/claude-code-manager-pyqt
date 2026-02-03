#!/usr/bin/env python3
"""
Claude Code Manager - A comprehensive GUI for managing Claude Code sessions, agents, and analytics.
"""

import sys
import os
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPalette, QColor

from ui.main_window import MainWindow
from core.config import Config


def setup_dark_palette(app: QApplication) -> None:
    """Configure dark mode palette for the application."""
    palette = QPalette()

    # Base colors
    palette.setColor(QPalette.Window, QColor(30, 30, 30))
    palette.setColor(QPalette.WindowText, QColor(220, 220, 220))
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(35, 35, 35))
    palette.setColor(QPalette.ToolTipBase, QColor(50, 50, 50))
    palette.setColor(QPalette.ToolTipText, QColor(220, 220, 220))
    palette.setColor(QPalette.Text, QColor(220, 220, 220))
    palette.setColor(QPalette.Button, QColor(45, 45, 45))
    palette.setColor(QPalette.ButtonText, QColor(220, 220, 220))
    palette.setColor(QPalette.BrightText, QColor(255, 255, 255))
    palette.setColor(QPalette.Link, QColor(100, 149, 237))
    palette.setColor(QPalette.Highlight, QColor(100, 100, 180))
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))

    # Disabled colors
    palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(128, 128, 128))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(128, 128, 128))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(128, 128, 128))

    app.setPalette(palette)


def main():
    """Main entry point for the application."""
    # Enable High DPI scaling
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("Claude Code Manager")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Claude")

    # Set default font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Apply dark palette
    setup_dark_palette(app)

    # Apply stylesheet
    app.setStyleSheet(get_stylesheet())

    # Initialize configuration
    config = Config()

    # Create and show main window
    window = MainWindow(config)
    window.show()

    sys.exit(app.exec_())


def get_stylesheet() -> str:
    """Return the application stylesheet."""
    return """
    QMainWindow {
        background-color: #1e1e1e;
    }

    QWidget {
        background-color: #1e1e1e;
        color: #dcdcdc;
    }

    QTabWidget::pane {
        border: 1px solid #3d3d3d;
        background-color: #252526;
        border-radius: 4px;
    }

    QTabBar::tab {
        background-color: #2d2d2d;
        color: #dcdcdc;
        padding: 10px 20px;
        margin-right: 2px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }

    QTabBar::tab:selected {
        background-color: #3d3d3d;
        border-bottom: 2px solid #6495ed;
    }

    QTabBar::tab:hover:!selected {
        background-color: #353535;
    }

    QTreeWidget, QListWidget, QTableWidget {
        background-color: #252526;
        border: 1px solid #3d3d3d;
        border-radius: 4px;
        selection-background-color: #094771;
    }

    QTreeWidget::item, QListWidget::item {
        padding: 5px;
        border-radius: 2px;
    }

    QTreeWidget::item:hover, QListWidget::item:hover {
        background-color: #2a2d2e;
    }

    QTreeWidget::item:selected, QListWidget::item:selected {
        background-color: #094771;
    }

    QHeaderView::section {
        background-color: #2d2d2d;
        color: #dcdcdc;
        padding: 8px;
        border: none;
        border-right: 1px solid #3d3d3d;
    }

    QPushButton {
        background-color: #0e639c;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
        font-weight: bold;
    }

    QPushButton:hover {
        background-color: #1177bb;
    }

    QPushButton:pressed {
        background-color: #094771;
    }

    QPushButton:disabled {
        background-color: #3d3d3d;
        color: #808080;
    }

    QPushButton[secondary="true"] {
        background-color: #3d3d3d;
        color: #dcdcdc;
    }

    QPushButton[secondary="true"]:hover {
        background-color: #4d4d4d;
    }

    QPushButton[danger="true"] {
        background-color: #c42b1c;
    }

    QPushButton[danger="true"]:hover {
        background-color: #d43b2c;
    }

    QLineEdit, QTextEdit, QPlainTextEdit {
        background-color: #3c3c3c;
        border: 1px solid #3d3d3d;
        border-radius: 4px;
        padding: 8px;
        color: #dcdcdc;
        selection-background-color: #094771;
    }

    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
        border: 1px solid #6495ed;
    }

    QComboBox {
        background-color: #3c3c3c;
        border: 1px solid #3d3d3d;
        border-radius: 4px;
        padding: 8px;
        color: #dcdcdc;
    }

    QComboBox::drop-down {
        border: none;
        padding-right: 10px;
    }

    QComboBox QAbstractItemView {
        background-color: #2d2d2d;
        border: 1px solid #3d3d3d;
        selection-background-color: #094771;
    }

    QScrollBar:vertical {
        background-color: #1e1e1e;
        width: 12px;
        border-radius: 6px;
    }

    QScrollBar::handle:vertical {
        background-color: #5a5a5a;
        border-radius: 6px;
        min-height: 30px;
    }

    QScrollBar::handle:vertical:hover {
        background-color: #6a6a6a;
    }

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }

    QScrollBar:horizontal {
        background-color: #1e1e1e;
        height: 12px;
        border-radius: 6px;
    }

    QScrollBar::handle:horizontal {
        background-color: #5a5a5a;
        border-radius: 6px;
        min-width: 30px;
    }

    QScrollBar::handle:horizontal:hover {
        background-color: #6a6a6a;
    }

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0px;
    }

    QGroupBox {
        border: 1px solid #3d3d3d;
        border-radius: 4px;
        margin-top: 12px;
        padding-top: 10px;
    }

    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 8px;
        color: #dcdcdc;
    }

    QLabel {
        color: #dcdcdc;
    }

    QSplitter::handle {
        background-color: #3d3d3d;
    }

    QSplitter::handle:hover {
        background-color: #6495ed;
    }

    QToolTip {
        background-color: #2d2d2d;
        color: #dcdcdc;
        border: 1px solid #3d3d3d;
        padding: 4px;
        border-radius: 4px;
    }

    QMenu {
        background-color: #2d2d2d;
        border: 1px solid #3d3d3d;
        border-radius: 4px;
        padding: 4px;
    }

    QMenu::item {
        padding: 8px 24px;
        border-radius: 2px;
    }

    QMenu::item:selected {
        background-color: #094771;
    }

    QStatusBar {
        background-color: #007acc;
        color: white;
    }

    QProgressBar {
        background-color: #3c3c3c;
        border: none;
        border-radius: 4px;
        text-align: center;
        color: white;
    }

    QProgressBar::chunk {
        background-color: #0e639c;
        border-radius: 4px;
    }

    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border-radius: 3px;
        border: 1px solid #3d3d3d;
        background-color: #3c3c3c;
    }

    QCheckBox::indicator:checked {
        background-color: #0e639c;
        border-color: #0e639c;
    }

    QSpinBox, QDoubleSpinBox {
        background-color: #3c3c3c;
        border: 1px solid #3d3d3d;
        border-radius: 4px;
        padding: 6px;
        color: #dcdcdc;
    }

    QSlider::groove:horizontal {
        height: 6px;
        background-color: #3c3c3c;
        border-radius: 3px;
    }

    QSlider::handle:horizontal {
        width: 16px;
        height: 16px;
        margin: -5px 0;
        background-color: #0e639c;
        border-radius: 8px;
    }

    QSlider::handle:horizontal:hover {
        background-color: #1177bb;
    }
    """


if __name__ == "__main__":
    main()
