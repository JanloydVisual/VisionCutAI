from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton

class BatchProgressPanel(QWidget):
    """
    UI Panel to monitor batch background removal progress.
    """
    def __init__(self, batch_manager, parent=None):
        super().__init__(parent)
        self.batch_manager = batch_manager
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        lbl_title = QLabel("Batch Processing Queue")
        lbl_title.setStyleSheet("font-weight: bold; color: #5dade2;")
        layout.addWidget(lbl_title)
        
        # Stats
        self.lbl_current = QLabel("Current Clip: None")
        self.lbl_stats = QLabel("Completed: 0 | Failed: 0 | Total: 0")
        layout.addWidget(self.lbl_current)
        layout.addWidget(self.lbl_stats)
        
        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Controls
        controls = QHBoxLayout()
        self.btn_start = QPushButton("Start Batch")
        self.btn_start.clicked.connect(self._start_batch)
        controls.addWidget(self.btn_start)
        
        self.btn_resume = QPushButton("Resume Failed")
        self.btn_resume.clicked.connect(self._resume_failed)
        controls.addWidget(self.btn_resume)
        
        layout.addLayout(controls)
        layout.addStretch()

    def _start_batch(self):
        self.batch_manager.process_queue()
        self.update_ui()
        
    def _resume_failed(self):
        self.batch_manager.resume_failed_jobs()
        self.update_ui()

    def update_ui(self):
        status = self.batch_manager.get_status()
        self.lbl_current.setText(f"Current Clip: {status['current_clip'] or 'Done'}")
        self.lbl_stats.setText(f"Completed: {status['completed_count']} | Failed: {status['failed_count']} | Total: {status['total_jobs']}")
        self.progress_bar.setValue(int(status['percentage']))
