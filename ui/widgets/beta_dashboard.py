from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFormLayout, QGroupBox, QPushButton, QHBoxLayout

class BetaDashboard(QWidget):
    """
    Internal telemetry dashboard to review aggregated external Beta session data.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Beta Analytics Dashboard")
        self.layout = QVBoxLayout(self)
        
        group = QGroupBox("Beta Field Analytics")
        form = QFormLayout(group)
        
        self.total_sessions_lbl = QLabel("0")
        self.completed_projects_lbl = QLabel("0")
        self.avg_mask_creation_lbl = QLabel("0s")
        self.refinement_count_lbl = QLabel("0")
        self.tracking_recovery_rate_lbl = QLabel("0%")
        self.export_success_lbl = QLabel("0%")
        
        form.addRow("Total Sessions:", self.total_sessions_lbl)
        form.addRow("Completed Projects:", self.completed_projects_lbl)
        form.addRow("Avg Mask Creation Time:", self.avg_mask_creation_lbl)
        form.addRow("Total Refinement Clicks:", self.refinement_count_lbl)
        form.addRow("Tracking Recovery Rate:", self.tracking_recovery_rate_lbl)
        form.addRow("Export Success Rate:", self.export_success_lbl)
        
        self.layout.addWidget(group)
        
        btn_layout = QHBoxLayout()
        self.export_btn = QPushButton("Export Beta Report")
        self.close_btn = QPushButton("Close")
        btn_layout.addWidget(self.export_btn)
        btn_layout.addWidget(self.close_btn)
        
        self.layout.addLayout(btn_layout)
        self.layout.addStretch()
