"""
Export Panel
------------
Workspace sidebar panel for export configuration.
Provides one-click export with remembered settings.
"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QComboBox,
    QFileDialog,
)
from PyQt6.QtCore import Qt, QSettings, pyqtSignal
import os
import subprocess


class ExportPanel(QWidget):
    """Export configuration panel for the workspace sidebar."""

    export_requested = pyqtSignal(str, str, str)  # output_dir, output_name, output_format

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings("VisionCutAI", "VisionCutAI")

        self._build_ui()
        self._load_settings()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        # Title
        title = QLabel("EXPORT")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #ddd;")
        layout.addWidget(title)

        # Output folder section
        layout.addWidget(QLabel("Output Folder"))

        self.folder_label = QLabel("")
        self.folder_label.setStyleSheet("color: #888; font-size: 11px; background: #2b2b2b; padding: 6px; border-radius: 4px;")
        self.folder_label.setWordWrap(True)
        layout.addWidget(self.folder_label)

        folder_btn_layout = QHBoxLayout()
        folder_btn_layout.setSpacing(6)

        self.change_folder_btn = QPushButton("Change Folder")
        self.change_folder_btn.clicked.connect(self._change_folder)
        folder_btn_layout.addWidget(self.change_folder_btn)

        self.open_folder_btn = QPushButton("Open Folder")
        self.open_folder_btn.clicked.connect(self._open_folder)
        self.open_folder_btn.setEnabled(False)
        folder_btn_layout.addWidget(self.open_folder_btn)

        layout.addLayout(folder_btn_layout)

        # Separator
        layout.addWidget(self._create_separator())

        # Output name section
        layout.addWidget(QLabel("Output Name"))

        self.name_input = QLineEdit()
        self.name_input.setStyleSheet("""
            QLineEdit {
                padding: 6px;
                background-color: #2b2b2b;
                border: 1px solid #444;
                border-radius: 4px;
                color: #ddd;
            }
        """)
        self.name_input.textChanged.connect(self._on_name_changed)
        layout.addWidget(self.name_input)

        # Separator
        layout.addWidget(self._create_separator())

        # Output format section
        layout.addWidget(QLabel("Output Format"))

        self.format_combo = QComboBox()
        self.format_combo.setStyleSheet("""
            QComboBox {
                padding: 6px;
                background-color: #2b2b2b;
                border: 1px solid #444;
                border-radius: 4px;
                color: #ddd;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        # Format options - architecture prepared for future formats
        self.format_combo.addItems([
            "PNG (Image)",            # Single image export
            "PNG Sequence (Video)",   # Video frames as PNG sequence
            "Transparent WebM",     # Future: WebM with alpha
            "MOV Alpha",            # Future: MOV with alpha
        ])
        self.format_combo.currentIndexChanged.connect(self._on_format_changed)
        # Future formats (now enabled)
        # self.format_combo.model().item(2).setEnabled(False)  # WebM
        # self.format_combo.model().item(3).setEnabled(False)  # MOV
        layout.addWidget(self.format_combo)

        # Export button
        layout.addStretch(1)

        self.export_btn = QPushButton("Export")
        self.export_btn.setMinimumHeight(40)
        self.export_btn.clicked.connect(self._on_export_clicked)
        self.export_btn.setStyleSheet("""
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
            QPushButton:disabled {
                background-color: #555;
            }
        """)
        layout.addWidget(self.export_btn)

    def _create_separator(self):
        """Create a horizontal separator line."""
        line = QWidget()
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: #444; margin: 4px 0;")
        return line

    def _load_settings(self):
        """Load saved settings from QSettings."""
        self._default_folder = self.settings.value("default_export_folder", "", type=str)
        self._output_name = self.settings.value("export_output_name", "export", type=str)
        
        # Override any previous default with MOV Alpha (index 3) to comply with new workflow
        self._output_format = 3

        self.name_input.setText(self._output_name)
        self.format_combo.setCurrentIndex(self._output_format)

        if self._default_folder:
            self.folder_label.setText(self._default_folder)
            self.open_folder_btn.setEnabled(True)

    def _save_settings(self):
        """Save settings to QSettings."""
        self.settings.setValue("export_output_name", self.name_input.text())
        self.settings.setValue("export_output_format", self.format_combo.currentIndex())

    def _change_folder(self):
        """Open folder browser dialog."""
        current = self._default_folder or os.path.expanduser("~")

        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Export Folder",
            current,
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontUseNativeDialog,
        )

        if folder:
            self._default_folder = folder
            self.folder_label.setText(folder)
            self.open_folder_btn.setEnabled(True)
            self.settings.setValue("default_export_folder", folder)
            self._save_settings()

    def _open_folder(self):
        """Open the export folder in file explorer."""
        if self._default_folder and os.path.exists(self._default_folder):
            subprocess.run(["explorer", os.path.normpath(self._default_folder)], shell=True)

    def _on_name_changed(self, text: str):
        """Handle output name changes."""
        self._output_name = text
        self._save_settings()

    def _on_format_changed(self, index: int):
        """Handle format selection changes."""
        self._output_format = index
        self._save_settings()

    def _on_export_clicked(self):
        """Handle export button click."""
        if not self._default_folder:
            # No folder set - ask for one
            self._change_folder()
            if not self._default_folder:
                return

        output_name = self.name_input.text().strip()
        if not output_name:
            output_name = "export"

        output_format = self.format_combo.currentText()

        self.export_requested.emit(self._default_folder, output_name, output_format)

    def set_export_enabled(self, enabled: bool):
        """Enable or disable the export button."""
        self.export_btn.setEnabled(enabled)

    def has_output_folder(self) -> bool:
        """Check if an output folder is configured."""
        return bool(self._default_folder)

    def get_output_folder(self) -> str:
        """Get the current output folder."""
        return self._default_folder or ""

    def get_output_name(self) -> str:
        """Get the current output name."""
        return self.name_input.text().strip() or "export"

    def get_output_format(self) -> str:
        """Get the current output format."""
        return self.format_combo.currentText()

    def update_output_name(self, filename: str):
        """Update the output name based on the opened media file."""
        name = os.path.splitext(os.path.basename(filename))[0]
        self.name_input.setText(name)
        self._output_name = name
        self._save_settings()