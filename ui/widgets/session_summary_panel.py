from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFormLayout, QGroupBox

class SessionSummaryPanel(QWidget):
    """
    Displays the final session UX metrics and workflow efficiency data.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        group = QGroupBox("User Session Summary")
        form = QFormLayout(group)
        
        self.workflow_duration_lbl = QLabel("0s")
        self.mask_quality_lbl = QLabel("N/A")
        self.corrections_needed_lbl = QLabel("0 clicks")
        self.tracking_health_lbl = QLabel("Perfect")
        self.export_performance_lbl = QLabel("0 fps")
        
        form.addRow("Workflow Duration:", self.workflow_duration_lbl)
        form.addRow("Mask Quality:", self.mask_quality_lbl)
        form.addRow("Corrections Needed:", self.corrections_needed_lbl)
        form.addRow("Tracking Health:", self.tracking_health_lbl)
        form.addRow("Export Performance:", self.export_performance_lbl)
        
        self.layout.addWidget(group)
        self.layout.addStretch()
        
    def update_summary(self, duration: str, quality: str, corrections: str, health: str, export: str):
        self.workflow_duration_lbl.setText(duration)
        self.mask_quality_lbl.setText(quality)
        self.corrections_needed_lbl.setText(corrections)
        self.tracking_health_lbl.setText(health)
        self.export_performance_lbl.setText(export)
