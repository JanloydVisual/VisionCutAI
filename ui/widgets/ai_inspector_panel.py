from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFormLayout, QGroupBox

class AIInspectorPanel(QWidget):
    """
    Detailed readout for the currently active object layer and tracking state.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        group = QGroupBox("AI Inspector")
        form = QFormLayout(group)
        
        self.active_object_lbl = QLabel("None")
        self.mask_quality_lbl = QLabel("N/A")
        self.tracking_confidence_lbl = QLabel("0%")
        self.cache_status_lbl = QLabel("Idle")
        self.workflow_preset_lbl = QLabel("Fast Preview")
        self.last_event_lbl = QLabel("None")
        
        form.addRow("Active Object:", self.active_object_lbl)
        form.addRow("Mask Quality:", self.mask_quality_lbl)
        form.addRow("Tracking Confidence:", self.tracking_confidence_lbl)
        form.addRow("Cache Status:", self.cache_status_lbl)
        form.addRow("Workflow Preset:", self.workflow_preset_lbl)
        form.addRow("Last AI Event:", self.last_event_lbl)
        
        self.layout.addWidget(group)
        self.layout.addStretch()
