from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton

class PresetPanel(QWidget):
    def __init__(self, preset_manager, parent=None):
        super().__init__(parent)
        self.preset_manager = preset_manager
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        
        lbl_title = QLabel("Workflow Presets")
        lbl_title.setStyleSheet("font-weight: bold; color: #5dade2;")
        layout.addWidget(lbl_title)
        
        controls_layout = QHBoxLayout()
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(self.preset_manager.get_preset_names())
        controls_layout.addWidget(self.preset_combo)
        
        btn_load = QPushButton("Load")
        btn_load.clicked.connect(self._load_preset)
        controls_layout.addWidget(btn_load)
        
        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self._save_preset)
        controls_layout.addWidget(btn_save)
        
        btn_del = QPushButton("Delete")
        btn_del.clicked.connect(self._delete_preset)
        controls_layout.addWidget(btn_del)
        
        layout.addLayout(controls_layout)
        layout.addStretch()

    def _load_preset(self):
        name = self.preset_combo.currentText()
        if name:
            self.preset_manager.load_preset(name)
            
    def _save_preset(self):
        # Mock save
        name = f"Custom {self.preset_combo.count()}"
        self.preset_manager.save_preset(name, {}, {}, {})
        self.preset_combo.addItem(name)
        
    def _delete_preset(self):
        name = self.preset_combo.currentText()
        if name != "Default":
            self.preset_manager.delete_preset(name)
            idx = self.preset_combo.findText(name)
            if idx >= 0:
                self.preset_combo.removeItem(idx)
