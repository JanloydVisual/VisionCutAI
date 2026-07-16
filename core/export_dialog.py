"""
Export Dialog
-------------
Professional export dialog with output name, folder selection, and type options.
"""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QComboBox,
    QCheckBox,
)
from PyQt6.QtCore import Qt, QSettings, pyqtSignal
import os


class ExportDialog(QDialog):
    """Professional export dialog for image and video exports."""

    def __init__(self, parent=None, is_video=True, default_name="export"):
        super().__init__(parent)
        self.settings = QSettings("VisionCutAI", "VisionCutAI")
        self.is_video = is_video
        self.output_path = None
        self.output_type = None

        self.setWindowTitle("Export")
        self.setModal(True)
        self.resize(450, 200)
        self.setMinimumWidth(400)

        self._build_ui(default_name)
        self._restore_settings()

    def _build_ui(self, default_name):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("Export Settings")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ddd;")
        layout.addWidget(title)

        # Output name
        layout.addWidget(QLabel("Output Name:"))
        self.name_input = QLineEdit(default_name)
        self.name_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                background-color: #2b2b2b;
                border: 1px solid #444;
                border-radius: 4px;
                color: #ddd;
            }
        """)
        layout.addWidget(self.name_input)

        # Output folder
        folder_layout = QHBoxLayout()
        folder_layout.setSpacing(8)

        layout.addWidget(QLabel("Output Folder:"))
        self.folder_input = QLineEdit()
        self.folder_input.setReadOnly(True)
        self.folder_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                background-color: #2b2b2b;
                border: 1px solid #444;
                border-radius: 4px;
                color: #ddd;
            }
        """)
        folder_layout.addWidget(self.folder_input)

        self.browse_button = QPushButton("Browse...")
        self.browse_button.setFixedWidth(90)
        self.browse_button.clicked.connect(self._browse_folder)
        folder_layout.addWidget(self.browse_button)
        layout.addLayout(folder_layout)

        # Output type
        layout.addWidget(QLabel("Output Type:"))
        self.type_combo = QComboBox()
        self.type_combo.setStyleSheet("""
            QComboBox {
                padding: 8px;
                background-color: #2b2b2b;
                border: 1px solid #444;
                border-radius: 4px;
                color: #ddd;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #2b2b2b;
                color: #ddd;
                selection-background-color: #2d7d46;
            }
        """)

        if self.is_video:
            self.type_combo.addItems(["PNG Sequence"])
        else:
            self.type_combo.addItems(["PNG"])

        layout.addWidget(self.type_combo)

        # Remember last folder
        self.remember_checkbox = QCheckBox("Remember last folder")
        self.remember_checkbox.setChecked(True)
        layout.addWidget(self.remember_checkbox)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        self.export_button = QPushButton("Export")
        self.export_button.setDefault(True)
        self.export_button.clicked.connect(self._on_export)
        self.export_button.setStyleSheet("""
            QPushButton {
                background-color: #2d7d46;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3a9d5a;
            }
        """)
        button_layout.addWidget(self.export_button)

        layout.addLayout(button_layout)

    def _restore_settings(self):
        """Restore last export folder from settings."""
        last_folder = self.settings.value("last_export_folder", "", type=str)
        if last_folder:
            self.folder_input.setText(last_folder)

    def _browse_folder(self):
        """Open folder browser dialog."""
        current = self.folder_input.text() or os.path.expanduser("~")

        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Output Folder",
            current,
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontUseNativeDialog,
        )

        if folder:
            self.folder_input.setText(folder)

    def _on_export(self):
        """Handle export button click."""
        name = self.name_input.text().strip()
        folder = self.folder_input.text().strip()

        if not name:
            self.name_input.setStyleSheet("""
                QLineEdit {
                    padding: 8px;
                    background-color: #2b2b2b;
                    border: 2px solid #cc3333;
                    border-radius: 4px;
                    color: #ddd;
                }
            """)
            return

        if not folder:
            return

        # Save settings
        if self.remember_checkbox.isChecked():
            self.settings.setValue("last_export_folder", folder)
            self.settings.setValue("remember_last_folder", True)

        self.output_path = os.path.join(folder, name)
        self.output_type = self.type_combo.currentText()
        self.accept()

    def get_values(self):
        """Return the dialog values."""
        return {
            "path": self.output_path,
            "type": self.output_type,
            "remember_folder": self.remember_checkbox.isChecked(),
        }