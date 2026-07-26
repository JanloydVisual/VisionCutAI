from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QComboBox
from core.render.preview_mode import PreviewMode

class PreviewQualitySelector(QWidget):
    """
    Toolbar UI component allowing users to switch between FAST, BALANCED, and FINAL preview modes.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.label = QLabel("Preview Quality:")
        self.combo = QComboBox()
        
        for mode in PreviewMode:
            self.combo.addItem(mode.name)
            
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.combo)
        
        self.combo.currentTextChanged.connect(self._on_quality_changed)
        
    def _on_quality_changed(self, text: str):
        # Sends signal to core renderer to update quality
        pass
