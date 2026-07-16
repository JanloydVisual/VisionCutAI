"""
PlaybackControls
----------------
Play / Pause / Stop / Remove Background buttons.
Emits signals - never calls VideoEngine or Controller directly.
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PyQt6.QtCore import pyqtSignal


class PlaybackControls(QWidget):
    play_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    remove_bg_clicked = pyqtSignal()
    ai_mode_changed = pyqtSignal(str)
    target_object_toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self.play_button = QPushButton("Play")
        self.pause_button = QPushButton("Pause")
        self.stop_button = QPushButton("Stop")

        for btn in (self.play_button, self.pause_button, self.stop_button):
            btn.setMinimumWidth(80)
            layout.addWidget(btn)

        layout.addStretch(1)

        from PyQt6.QtWidgets import QComboBox
        
        # AI Mode Dropdown
        self.ai_mode_combo = QComboBox()
        self.ai_mode_combo.addItem("High Quality", "u2net")
        self.ai_mode_combo.addItem("Balanced", "silueta")
        self.ai_mode_combo.addItem("Draft (Fast)", "u2netp")
        self.ai_mode_combo.setToolTip("Select AI Quality vs Speed")
        layout.addWidget(self.ai_mode_combo)

        # Remove Background button - primary action, visually distinct
        self.remove_bg_button = QPushButton("Remove Background")
        self.remove_bg_button.setMinimumWidth(140)
        self.remove_bg_button.setEnabled(False)
        self.remove_bg_button.setStyleSheet("""
            QPushButton {
                background-color: #2d7d46;
                color: white;
                font-weight: bold;
                padding: 4px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3a9d5a;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #999;
            }
        """)
        layout.addWidget(self.remove_bg_button)

        self.play_button.clicked.connect(self.play_clicked.emit)
        self.pause_button.clicked.connect(self.pause_clicked.emit)
        self.stop_button.clicked.connect(self.stop_clicked.emit)
        self.remove_bg_button.clicked.connect(self.remove_bg_clicked.emit)
        self.ai_mode_combo.currentDataChanged = lambda: self.ai_mode_changed.emit(self.ai_mode_combo.currentData())
        self.ai_mode_combo.currentIndexChanged.connect(self.ai_mode_combo.currentDataChanged)

        # Target Object button
        self.target_object_button = QPushButton("Select Target")
        self.target_object_button.setCheckable(True)
        self.target_object_button.setToolTip("Draw a rectangle or click on the video to select target object")
        layout.insertWidget(layout.indexOf(self.remove_bg_button), self.target_object_button)

        self.target_object_button.toggled.connect(self.target_object_toggled.emit)

    def set_playing_state(self, is_playing: bool) -> None:
        self.play_button.setEnabled(not is_playing)
        self.pause_button.setEnabled(is_playing)

    def set_controls_enabled(self, enabled: bool) -> None:
        self.play_button.setEnabled(enabled)
        self.pause_button.setEnabled(enabled)
        self.stop_button.setEnabled(enabled)

    def set_remove_bg_enabled(self, enabled: bool) -> None:
        self.remove_bg_button.setEnabled(enabled)

    def set_remove_bg_text(self, text: str) -> None:
        self.remove_bg_button.setText(text)

    def set_remove_bg_processing(self, processing: bool) -> None:
        """Set button to processing state with spinner animation indicator."""
        if processing:
            self.remove_bg_button.setText("Processing...")
            self.remove_bg_button.setStyleSheet("""
                QPushButton {
                    background-color: #cc9900;
                    color: white;
                    font-weight: bold;
                    padding: 4px 12px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #e6b800;
                }
                QPushButton:disabled {
                    background-color: #555;
                    color: #999;
                }
            """)
            self.remove_bg_button.setEnabled(False)
        else:
            self.set_remove_bg_ready()

    def set_remove_bg_ready(self) -> None:
        """Set button to ready state (Remove Background)."""
        self.remove_bg_button.setText("Remove Background")
        self.remove_bg_button.setStyleSheet("""
            QPushButton {
                background-color: #2d7d46;
                color: white;
                font-weight: bold;
                padding: 4px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3a9d5a;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #999;
            }
        """)

    def set_remove_bg_complete(self) -> None:
        """Set button to complete state (Background Removed)."""
        self.remove_bg_button.setText("Background Removed ✓")
        self.remove_bg_button.setStyleSheet("""
            QPushButton {
                background-color: #2d7d46;
                color: white;
                font-weight: bold;
                padding: 4px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3a9d5a;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #999;
            }
        """)
        self.remove_bg_button.setEnabled(False)
