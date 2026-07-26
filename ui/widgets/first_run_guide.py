from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import pyqtSignal

class FirstRunGuide(QWidget):
    """
    Onboarding UI to guide first-time beta users through the core VisionCut AI workflow.
    """
    step_completed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_step = 0
        self.steps = [
            {"id": "import", "title": "Step 1: Import Video", "desc": "Drag and drop your footage into the timeline to begin."},
            {"id": "mask", "title": "Step 2: Create Mask", "desc": "Use the Magic Brush to draw a quick stroke over your subject."},
            {"id": "review", "title": "Step 3: Review", "desc": "Check the AI Timeline Assistant for any flagged tracking issues."},
            {"id": "export", "title": "Step 4: Export", "desc": "Click 'Export for Resolve' to generate your final alpha sequence."}
        ]
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 12, 12, 12)
        
        self.lbl_title = QLabel()
        self.lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #5dade2;")
        self.layout.addWidget(self.lbl_title)
        
        self.lbl_desc = QLabel()
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setStyleSheet("font-size: 13px; color: #a9b7c6;")
        self.layout.addWidget(self.lbl_desc)
        
        self.btn_next = QPushButton("Got it")
        self.btn_next.clicked.connect(self._advance_step)
        self.layout.addWidget(self.btn_next)
        
        self.layout.addStretch()
        self._update_ui()

    def _update_ui(self):
        if self.current_step < len(self.steps):
            step = self.steps[self.current_step]
            self.lbl_title.setText(step["title"])
            self.lbl_desc.setText(step["desc"])
        else:
            self.lbl_title.setText("You're ready!")
            self.lbl_desc.setText("Enjoy using VisionCut AI.")
            self.btn_next.setVisible(False)

    def _advance_step(self):
        if self.current_step < len(self.steps):
            self.step_completed.emit(self.steps[self.current_step]["id"])
            self.current_step += 1
            self._update_ui()
