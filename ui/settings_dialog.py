from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget, 
                             QStackedWidget, QWidget, QLabel, QPushButton, 
                             QFormLayout, QLineEdit, QComboBox, QCheckBox)
from PyQt6.QtCore import Qt, QSettings

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(700, 450)
        self.setStyleSheet("background-color: #2b2b2b; color: #d4d4d4;")
        
        self.settings = QSettings("VisionCutAI", "VisionCutAI")
        
        main_layout = QHBoxLayout(self)
        
        self.list_widget = QListWidget()
        self.list_widget.setFixedWidth(150)
        self.list_widget.setStyleSheet("QListWidget { background-color: #1e1e1e; border: none; } "
                                       "QListWidget::item { padding: 10px; } "
                                       "QListWidget::item:selected { background-color: #5dade2; color: #1e1e1e; }")
        
        self.stack = QStackedWidget()
        
        # Categories
        self.add_category("Workspace", self._create_workspace_page())
        self.add_category("Playback", self._create_playback_page())
        self.add_category("AI", self._create_ai_page())
        self.add_category("Performance", self._create_performance_page())
        self.add_category("Export", self._create_export_page())
        self.add_category("Developer", self._create_developer_page())
        
        self.list_widget.currentRowChanged.connect(self.stack.setCurrentIndex)
        
        main_layout.addWidget(self.list_widget)
        
        right_layout = QVBoxLayout()
        right_layout.addWidget(self.stack)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self.save_and_accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        
        right_layout.addLayout(btn_layout)
        main_layout.addLayout(right_layout)

    def add_category(self, name, widget):
        self.list_widget.addItem(name)
        self.stack.addWidget(widget)

    def _create_workspace_page(self):
        page = QWidget()
        layout = QFormLayout(page)
        
        self.inp_proj_folder = QLineEdit(self.settings.value("Workspace/default_project_folder", "~/Documents/VisionCut"))
        self.inp_cache_folder = QLineEdit(self.settings.value("Workspace/cache_folder", "temp/"))
        self.cmb_theme = QComboBox()
        self.cmb_theme.addItems(["Dark", "Light", "System"])
        self.cmb_theme.setCurrentText(self.settings.value("Workspace/theme", "Dark"))
        
        self.chk_auto_open = QCheckBox("Auto-open last project")
        self.chk_auto_open.setChecked(self.settings.value("Workspace/auto_open", True, type=bool))
        
        layout.addRow("Default Project Folder:", self.inp_proj_folder)
        layout.addRow("Cache Folder:", self.inp_cache_folder)
        layout.addRow("Theme:", self.cmb_theme)
        layout.addRow("", self.chk_auto_open)
        
        return page

    def _create_playback_page(self):
        page = QWidget()
        layout = QFormLayout(page)
        self.cmb_preview = QComboBox()
        self.cmb_preview.addItems(["Full Resolution", "Half Resolution", "Quarter Resolution"])
        self.cmb_preview.setCurrentText(self.settings.value("Playback/preview_quality", "Full Resolution"))
        layout.addRow("Preview Quality:", self.cmb_preview)
        return page

    def _create_ai_page(self):
        page = QWidget()
        layout = QFormLayout(page)
        self.cmb_device = QComboBox()
        self.cmb_device.addItems(["CUDA", "CPU"])
        self.cmb_device.setCurrentText(self.settings.value("AI/device", "CUDA"))
        layout.addRow("Compute Device:", self.cmb_device)
        return page

    def _create_performance_page(self):
        page = QWidget()
        layout = QFormLayout(page)
        self.inp_ram = QLineEdit(self.settings.value("Performance/ram_preload", "60"))
        layout.addRow("RAM Preload Size (Frames):", self.inp_ram)
        return page

    def _create_export_page(self):
        page = QWidget()
        layout = QFormLayout(page)
        self.cmb_priority = QComboBox()
        self.cmb_priority.addItems(["Normal", "High", "Realtime"])
        self.cmb_priority.setCurrentText(self.settings.value("Export/priority", "Normal"))
        layout.addRow("Render Priority:", self.cmb_priority)
        return page

    def _create_developer_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Developer settings are configured via the VISIONCUT_ENV environment variable."))
        layout.addStretch()
        return page

    def save_and_accept(self):
        self.settings.setValue("Workspace/default_project_folder", self.inp_proj_folder.text())
        self.settings.setValue("Workspace/cache_folder", self.inp_cache_folder.text())
        self.settings.setValue("Workspace/theme", self.cmb_theme.currentText())
        self.settings.setValue("Workspace/auto_open", self.chk_auto_open.isChecked())
        
        self.settings.setValue("Playback/preview_quality", self.cmb_preview.currentText())
        self.settings.setValue("AI/device", self.cmb_device.currentText())
        self.settings.setValue("Performance/ram_preload", self.inp_ram.text())
        self.settings.setValue("Export/priority", self.cmb_priority.currentText())
        
        self.accept()