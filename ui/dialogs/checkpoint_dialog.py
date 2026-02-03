"""
Checkpoint creation dialog.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QDialogButtonBox
)


class CheckpointDialog(QDialog):
    """Dialog for creating checkpoints."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Checkpoint")
        self.resize(400, 150)

        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter checkpoint name")
        form.addRow("Name:", self.name_input)

        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("Optional description")
        form.addRow("Description:", self.description_input)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self):
        """Get the entered values."""
        return (
            self.name_input.text().strip(),
            self.description_input.text().strip()
        )
