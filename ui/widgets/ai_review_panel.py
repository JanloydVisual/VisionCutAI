from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget
from PyQt6.QtCore import pyqtSignal

class AIReviewPanel(QWidget):
    """
    Dedicated UI for the Smart AI Review Workflow.
    Allows users to list issues, jump to them, compare masks, and sign off for export.
    """
    jump_requested = pyqtSignal(int)
    refinement_requested = pyqtSignal(int)
    
    def __init__(self, review_workflow, parent=None):
        super().__init__(parent)
        self.workflow = review_workflow
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        lbl_title = QLabel("Smart AI Review")
        lbl_title.setStyleSheet("font-weight: bold; color: #5dade2;")
        layout.addWidget(lbl_title)
        
        # Issue List
        self.issue_list = QListWidget()
        self.issue_list.itemClicked.connect(self._on_issue_selected)
        layout.addWidget(self.issue_list)
        
        # Actions
        actions = QHBoxLayout()
        self.btn_refine = QPushButton("Send to Refinement")
        self.btn_refine.clicked.connect(self._on_refine_clicked)
        actions.addWidget(self.btn_refine)
        
        self.btn_mark_reviewed = QPushButton("Mark Reviewed")
        self.btn_mark_reviewed.clicked.connect(self._on_mark_reviewed)
        actions.addWidget(self.btn_mark_reviewed)
        
        self.btn_compare = QPushButton("Before/After Viewer")
        self.btn_compare.clicked.connect(self._show_comparison)
        actions.addWidget(self.btn_compare)
        
        layout.addLayout(actions)
        
        # Approval Status
        self.lbl_status = QLabel("Status: Unknown")
        self.lbl_status.setStyleSheet("font-weight: bold; color: #a9b7c6;")
        layout.addWidget(self.lbl_status)
        
        self.refresh_issues()

    def refresh_issues(self):
        self.issue_list.clear()
        issues = self.workflow.get_issue_list()
        for i, issue in enumerate(issues):
            self.issue_list.addItem(f"Frame {issue['frame']} - {issue['type']}: {issue['description']}")
        self.update_status()

    def _on_issue_selected(self, item):
        text = item.text()
        frame_str = text.split(" ")[1]
        try:
            frame = int(frame_str)
            self.jump_requested.emit(frame)
        except ValueError:
            pass
            
    def _on_refine_clicked(self):
        item = self.issue_list.currentItem()
        if item:
            frame = int(item.text().split(" ")[1])
            self.workflow.send_to_refinement(frame)
            
    def _on_mark_reviewed(self):
        item = self.issue_list.currentItem()
        if item:
            frame = int(item.text().split(" ")[1])
            self.workflow.mark_reviewed(frame)
            self.update_status()
            
    def _show_comparison(self):
        item = self.issue_list.currentItem()
        if item:
            frame = int(item.text().split(" ")[1])
            self.workflow.generate_comparison_masks(frame)
            # Mock popup UI behavior
            
    def update_status(self):
        status = self.workflow.get_approval_status()
        ready_txt = "YES" if status['ready_for_export'] else "NO"
        self.lbl_status.setText(f"Reviewed: {status['reviewed_count']}/{status['total_issues']} | Score: {status['quality_score']:.1f}% | Ready: {ready_txt}")
