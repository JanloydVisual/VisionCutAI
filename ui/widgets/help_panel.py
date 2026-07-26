from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QScrollArea, QWidget,
    QLabel, QPushButton, QHBoxLayout, QFrame
)
from PyQt6.QtCore import Qt

from core.input.shortcut_manager import ShortcutManager

class HelpPanel(QDialog):
    """
    Floating help window detailing shortcuts, tools, and the AI workflow.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("VisionCut AI Help")
        self.setFixedSize(500, 600)
        
        main_layout = QVBoxLayout(self)
        
        # Scroll Area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content_widget = QWidget()
        self.layout = QVBoxLayout(content_widget)
        
        # Load keyboard shortcuts from get_shortcuts list
        shortcuts = ShortcutManager.get_shortcuts()
        shortcut_dict = {item["key"]: item["description"] for item in shortcuts}
        self._add_section("Keyboard Shortcuts", shortcut_dict)
        
        self._add_section("VisionCut Workflow", {
            "1. Setup": "Import video and set your target workflow preset.",
            "2. Select Object": "Create a new foreground object layer.",
            "3. Anchor": "Draw bounding box or points to segment the frame.",
            "4. Track": "Play forward. The AI tracks your object automatically.",
            "5. Refine": "Fix bad frames by adding new anchor points.",
            "6. Export": "Export your composite video."
        })
        
        self._add_section("AI Pipeline Explanation", {
            "Segmentation": "Uses MobileSAM to parse single frames.",
            "Tracking": "Uses Optical Flow to propagate masks temporally.",
            "Refinement": "Smooths edges and removes background noise.",
            "Compositing": "Combines multiple object layers sequentially."
        })
        
        self.layout.addStretch()
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        main_layout.addLayout(btn_layout)

    def _add_section(self, title: str, items: dict):
        header = QLabel(title)
        header.setStyleSheet("font-weight: bold; font-size: 16px; margin-top: 10px; color: #4DA8DA;")
        self.layout.addWidget(header)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        self.layout.addWidget(line)
        
        for k, v in items.items():
            row = QHBoxLayout()
            key_label = QLabel(f"{k} - {v}")
            key_label.setWordWrap(True)
            row.addWidget(key_label, stretch=1)
            self.layout.addLayout(row)
