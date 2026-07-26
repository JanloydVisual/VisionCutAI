from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt

class TimelineAIStatus(QWidget):
    """
    Overlay display for AI status directly on the timeline.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        
        self.lbl_quality = QLabel("Quality: -")
        self.lbl_confidence = QLabel("Confidence: -")
        self.lbl_cache = QLabel("Cache: -")
        
        for lbl in [self.lbl_quality, self.lbl_confidence, self.lbl_cache]:
            lbl.setStyleSheet("font-size: 10px; color: #a9b7c6; background-color: rgba(30, 30, 30, 180); border-radius: 2px;")
            layout.addWidget(lbl)
            
    def update_status(self, quality: str, confidence: float, cache_status: str):
        self.lbl_quality.setText(f"Quality: {quality}")
        self.lbl_confidence.setText(f"Confidence: {confidence:.1f}%")
        self.lbl_cache.setText(f"Cache: {cache_status}")
