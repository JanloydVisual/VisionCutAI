import os
import traceback
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTextEdit, QApplication)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

class ErrorDialog(QDialog):
    def __init__(self, title: str, message: str, exc_info: tuple = None, log_path: str = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(500)
        self.setStyleSheet("background-color: #2b2b2b; color: #e0e0e0;")
        
        layout = QVBoxLayout(self)
        
        lbl_msg = QLabel(message)
        lbl_msg.setWordWrap(True)
        lbl_msg.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(lbl_msg)
        
        self.details_edit = QTextEdit()
        self.details_edit.setReadOnly(True)
        self.details_edit.setStyleSheet("background-color: #1e1e1e; font-family: Consolas; font-size: 11px;")
        
        if exc_info:
            tb_str = "".join(traceback.format_exception(*exc_info))
            self.details_edit.setPlainText(tb_str)
        else:
            self.details_edit.setPlainText("No traceback available.")
            
        self.details_edit.hide()
        
        btn_layout = QHBoxLayout()
        
        self.btn_details = QPushButton("View Details")
        self.btn_details.clicked.connect(self.toggle_details)
        
        self.btn_logs = QPushButton("Open Crash Report")
        if log_path:
            self.btn_logs.clicked.connect(lambda: os.startfile(log_path))
        else:
            self.btn_logs.clicked.connect(lambda: os.startfile("crashes"))
        
        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.btn_details)
        btn_layout.addWidget(self.btn_logs)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_close)
        
        layout.addWidget(self.details_edit)
        layout.addLayout(btn_layout)
        
    def toggle_details(self):
        if self.details_edit.isVisible():
            self.details_edit.hide()
            self.btn_details.setText("View Details")
            self.resize(self.width(), self.minimumHeight())
        else:
            self.details_edit.show()
            self.btn_details.setText("Hide Details")
            self.resize(600, 400)
