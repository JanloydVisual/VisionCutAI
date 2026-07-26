from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import pyqtSignal

class ExportReadinessPanel(QWidget):
    """
    Panel to display the export readiness status based on timeline AI analysis.
    """
    jump_requested = pyqtSignal(int)
    
    def __init__(self, assistant, parent=None):
        super().__init__(parent)
        self.assistant = assistant
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        
        lbl_title = QLabel("Export Readiness")
        lbl_title.setStyleSheet("font-weight: bold; color: #5dade2;")
        layout.addWidget(lbl_title)
        
        # Readiness Metrics
        self.lbl_coverage = QLabel("Mask Coverage: -")
        self.lbl_stability = QLabel("Tracking Stability: -")
        self.lbl_reviews = QLabel("Frames Requiring Review: -")
        
        for lbl in [self.lbl_coverage, self.lbl_stability, self.lbl_reviews]:
            layout.addWidget(lbl)
            
        # Navigation
        nav_layout = QHBoxLayout()
        btn_prev = QPushButton("Previous Issue")
        btn_prev.clicked.connect(self._nav_previous)
        nav_layout.addWidget(btn_prev)
        
        btn_next = QPushButton("Next Issue")
        btn_next.clicked.connect(self._nav_next)
        nav_layout.addWidget(btn_next)
        
        layout.addLayout(nav_layout)
        layout.addStretch()
        self.current_frame = 0

    def refresh_status(self, current_frame: int):
        self.current_frame = current_frame
        readiness = self.assistant.get_export_readiness()
        self.lbl_coverage.setText(f"Mask Coverage: {readiness['mask_coverage']:.1f}%")
        self.lbl_stability.setText(f"Tracking Stability: {readiness['tracking_stability']:.1f}%")
        self.lbl_reviews.setText(f"Frames Requiring Review: {readiness['frames_requiring_review']}")
        
    def _nav_previous(self):
        frame = self.assistant.get_previous_issue(self.current_frame)
        if frame >= 0:
            self.jump_requested.emit(frame)
            
    def _nav_next(self):
        frame = self.assistant.get_next_issue(self.current_frame)
        if frame >= 0:
            self.jump_requested.emit(frame)
