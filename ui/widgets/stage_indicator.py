"""
StageIndicator
--------------
Read-only display of the current workflow stage (Select Object / Track
Object / Remove Background). Purely a status display -- the controller
decides the active stage, this widget just reflects it.
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt


class StageIndicator(QWidget):

    STAGES = ["1. Select Object", "2. Track Object", "3. Remove Background"]

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        self._labels = []
        for i, text in enumerate(self.STAGES):
            label = QLabel(text)
            layout.addWidget(label)
            self._labels.append(label)

            if i < len(self.STAGES) - 1:
                arrow = QLabel("→")
                arrow.setStyleSheet("color: #555; font-size: 13px;")
                layout.addWidget(arrow)

        layout.addStretch(1)
        self._active_stage = 0
        self.set_active_stage(1)

    def set_active_stage(self, stage: int):
        """stage is 1-indexed (1, 2, or 3), matching Controller.workflow_stage."""
        if stage == self._active_stage:
            return
        self._active_stage = stage

        for i, label in enumerate(self._labels, start=1):
            if i == stage:
                label.setStyleSheet("""
                    color: #2d7d46;
                    font-weight: bold;
                    font-size: 12.5px;
                """)
            elif i < stage:
                label.setStyleSheet("""
                    color: #999;
                    font-weight: normal;
                    font-size: 12.5px;
                """)
            else:
                label.setStyleSheet("""
                    color: #555;
                    font-weight: normal;
                    font-size: 12.5px;
                """)
