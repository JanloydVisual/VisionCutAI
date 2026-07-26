from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QGroupBox, QFormLayout

class ProjectHealthPanel(QWidget):
    """
    Displays real-time metrics on mask quality, tracking stability, and cache state.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        # Health Group
        health_group = QGroupBox("Project Health")
        form_layout = QFormLayout(health_group)
        
        self.mask_quality_lbl = QLabel("High")
        self.tracking_stability_lbl = QLabel("Stable (1 Reanchor)")
        self.cache_state_lbl = QLabel("100% (256 MB)")
        self.reanchor_count_lbl = QLabel("1")
        self.export_time_lbl = QLabel("Est. 45s")
        
        form_layout.addRow("Mask Quality:", self.mask_quality_lbl)
        form_layout.addRow("Tracking Stability:", self.tracking_stability_lbl)
        form_layout.addRow("Cache State:", self.cache_state_lbl)
        form_layout.addRow("Auto Reanchors:", self.reanchor_count_lbl)
        form_layout.addRow("Export Time:", self.export_time_lbl)
        
        self.layout.addWidget(health_group)
        self.layout.addStretch()
        
    def update_metrics(self, mask_quality: str, stability: str, cache_state: str, reanchors: str, export_time: str):
        self.mask_quality_lbl.setText(mask_quality)
        self.tracking_stability_lbl.setText(stability)
        self.cache_state_lbl.setText(cache_state)
        self.reanchor_count_lbl.setText(reanchors)
        self.export_time_lbl.setText(export_time)
