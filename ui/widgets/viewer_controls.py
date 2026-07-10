"""
ViewerControls
--------------
Fit / 100% / 200% / Reset buttons + zoom percentage readout.
Emits signals only - never touches ViewerWidget directly.
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import pyqtSignal


class ViewerControls(QWidget):

    fit_clicked = pyqtSignal()
    zoom_100_clicked = pyqtSignal()
    zoom_200_clicked = pyqtSignal()
    reset_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)

        self.fit_button = QPushButton("Fit")
        self.zoom_100_button = QPushButton("100%")
        self.zoom_200_button = QPushButton("200%")
        self.reset_button = QPushButton("Reset")

        for btn in (self.fit_button, self.zoom_100_button, self.zoom_200_button, self.reset_button):
            btn.setFixedWidth(60)
            layout.addWidget(btn)

        layout.addStretch(1)

        self.zoom_label = QLabel("100%")
        self.zoom_label.setStyleSheet("color: #aaa; font-size: 11px;")
        layout.addWidget(self.zoom_label)

        self.fit_button.clicked.connect(self.fit_clicked.emit)
        self.zoom_100_button.clicked.connect(self.zoom_100_clicked.emit)
        self.zoom_200_button.clicked.connect(self.zoom_200_clicked.emit)
        self.reset_button.clicked.connect(self.reset_clicked.emit)

    def set_zoom_label(self, zoom_factor: float) -> None:
        self.zoom_label.setText(f"{int(round(zoom_factor * 100))}%")
