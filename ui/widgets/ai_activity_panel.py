from PyQt6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QGroupBox
from datetime import datetime

class AIActivityViewer(QWidget):
    """
    Displays a real-time stream of AI background events.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        group = QGroupBox("AI Activity Stream")
        group_layout = QVBoxLayout(group)
        
        self.event_list = QListWidget()
        group_layout.addWidget(self.event_list)
        
        self.layout.addWidget(group)
        
    def add_event(self, event_type: str, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.event_list.addItem(f"[{timestamp}] {event_type.upper()}: {message}")
        self.event_list.scrollToBottom()
