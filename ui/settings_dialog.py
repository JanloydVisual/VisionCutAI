"""
Settings Dialog
---------------
Application settings for VisionCut AI.
Includes: Default export folder, Remember last folder, GPU/CPU preference, Theme.
"""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QCheckBox,
    QPushButton,
    QFileDialog,
    QComboBox,
    QWidget,
)
from PyQt6.QtCore import Qt, QSettings
import os


class SettingsDialog(QDialog):
    """Application settings dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings("VisionCutAI", "VisionCutAI")

        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(450, 300)
        self.setMinimumWidth(400)

        self._build_ui()
        self._load_settings()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("Application Settings")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ddd;")
        layout.addWidget(title)

        # Export settings section
        export_group = QWidget()
        export_layout = QVBoxLayout(export_group)
        export_layout.setSpacing(10)
        export_layout.setContentsMargins(0, 0, 0, 0)

        # Default export folder
        export_layout.addWidget(QLabel("Export Settings"))

        folder_layout = QHBoxLayout()
        folder_layout.setSpacing(8)

        self.default_folder_input = QLabel("")
        self.default_folder_input.setStyleSheet("color: #888; font-size: 12px; padding: 4px;")
        self.default_folder_input.setMinimumWidth(200)
        folder_layout.addWidget(self.default_folder_input)

        self.folder_browse_button = QPushButton("Set Default Folder")
        self.folder_browse_button.clicked.connect(self._set_default_folder)
        folder_layout.addWidget(self.folder_browse_button)

        export_layout.addLayout(folder_layout)

        # Remember last folder
        self.remember_checkbox = QCheckBox("Remember last folder")
        export_layout.addWidget(self.remember_checkbox)

        layout.addWidget(export_group)

        # Processing settings section
        processing_group = QWidget()
        processing_layout = QVBoxLayout(processing_group)
        processing_layout.setSpacing(10)
        processing_layout.setContentsMargins(0, 0, 0, 0)

        processing_layout.addWidget(QLabel("Processing Settings"))

        # GPU/CPU preference
        self.device_combo = QComboBox()
        self.device_combo.addItems(["Auto (GPU if available)", "GPU Only", "CPU Only"])
        processing_layout.addWidget(self.device_combo)

        layout.addWidget(processing_group)

        # Theme settings section (future ready)
        theme_group = QWidget()
        theme_layout = QVBoxLayout(theme_group)
        theme_layout.setSpacing(10)
        theme_layout.setContentsMargins(0, 0, 0, 0)

        theme_layout.addWidget(QLabel("Appearance (Future)"))

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark (Default)", "Light", "System"])
        self.theme_combo.setCurrentIndex(0)
        theme_layout.addWidget(self.theme_combo)

        layout.addWidget(theme_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        self.save_button = QPushButton("Save")
        self.save_button.setDefault(True)
        self.save_button.clicked.connect(self._save_settings)
        self.save_button.setStyleSheet("""
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
        button_layout.addWidget(self.save_button)

        layout.addLayout(button_layout)

    def _load_settings(self):
        """Load settings from QSettings."""
        default_folder = self.settings.value("default_export_folder", "", type=str)
        self.default_folder_input.setText(default_folder or "Not set")

        remember = self.settings.value("remember_last_folder", True, type=bool)
        self.remember_checkbox.setChecked(remember)

        device_pref = self.settings.value("device_preference", 0, type=int)
        self.device_combo.setCurrentIndex(device_pref)

        theme_pref = self.settings.value("theme_preference", 0, type=int)
        self.theme_combo.setCurrentIndex(theme_pref)

    def _set_default_folder(self):
        """Set the default export folder."""
        current = self.settings.value("default_export_folder", "", type=str)
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Default Export Folder",
            current or os.path.expanduser("~"),
            QFileDialog.Option.ShowDirsOnly,
        )
        if folder:
            self.default_folder_input.setText(folder)

    def _save_settings(self):
        """Save settings to QSettings."""
        default_folder = self.default_folder_input.text()
        if default_folder and default_folder != "Not set":
            self.settings.setValue("default_export_folder", default_folder)

        self.settings.setValue("remember_last_folder", self.remember_checkbox.isChecked())
        self.settings.setValue("device_preference", self.device_combo.currentIndex())
        self.settings.setValue("theme_preference", self.theme_combo.currentIndex())

        self.accept()

    def get_device_preference(self) -> str:
        """Return the device preference as a string."""
        index = self.settings.value("device_preference", 0, type=int)
        if index == 0:
            return "auto"
        elif index == 1:
            return "gpu"
        else:
            return "cpu"

    def get_default_export_folder(self) -> str:
        """Return the default export folder."""
        return self.settings.value("default_export_folder", "", type=str)