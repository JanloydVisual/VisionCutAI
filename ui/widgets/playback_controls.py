"""
PlaybackControls
----------------
Play / Pause / Stop / Remove Background buttons.
Emits signals - never calls VideoEngine or Controller directly.
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QStyle
from PyQt6.QtCore import pyqtSignal


class PlaybackControls(QWidget):
    play_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    remove_bg_clicked = pyqtSignal()
    ai_mode_changed = pyqtSignal(str)
    target_object_toggled = pyqtSignal(bool)
    mask_mode_changed = pyqtSignal(int)
    prompt_mode_changed = pyqtSignal(str)
    clear_prompts_clicked = pyqtSignal()
    undo_prompt_clicked = pyqtSignal()
    apply_target_clicked = pyqtSignal()
    ai_quality_changed = pyqtSignal(str)
    render_priority_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(3)

        # Row 1: transport + AI model settings -- always visible.
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        outer.addLayout(layout)

        # Row 2: interactive object-selection toolset -- only meaningful
        # once "Select Target" is active, kept on its own row so it never
        # forces row 1's combo boxes to truncate their text.
        row2 = QHBoxLayout()
        row2.setContentsMargins(0, 0, 0, 0)
        outer.addLayout(row2)

        self.play_button = QPushButton()
        self.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.play_button.setToolTip("Play")

        self.pause_button = QPushButton()
        self.pause_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
        self.pause_button.setToolTip("Pause")

        self.stop_button = QPushButton()
        self.stop_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self.stop_button.setToolTip("Stop")

        for btn in (self.play_button, self.pause_button, self.stop_button):
            btn.setMinimumWidth(80)
            layout.addWidget(btn)

        layout.addStretch(1)

        from PyQt6.QtWidgets import QComboBox

        # AI Mode Dropdown
        self.ai_mode_combo = QComboBox()
        self.ai_mode_combo.addItem("Tracking (MobileSAM)", "sam")
        self.ai_mode_combo.addItem("High Quality (U2Net)", "u2net")
        self.ai_mode_combo.addItem("Balanced (Silueta)", "silueta")
        self.ai_mode_combo.addItem("Draft (Fast)", "u2netp")
        self.ai_mode_combo.setToolTip("Select AI Model")
        self.ai_mode_combo.setMinimumWidth(150)
        layout.addWidget(self.ai_mode_combo)

        self.ai_quality_combo = QComboBox()
        self.ai_quality_combo.addItem("Best Quality", "Best")
        self.ai_quality_combo.addItem("Balanced Scale", "Balanced")
        self.ai_quality_combo.addItem("Draft Scale", "Draft")
        self.ai_quality_combo.setToolTip("Select Proxy Inference Scale")
        self.ai_quality_combo.setMinimumWidth(110)
        layout.addWidget(self.ai_quality_combo)

        self.render_priority_combo = QComboBox()
        self.render_priority_combo.addItem("Normal Priority", "Normal")
        self.render_priority_combo.addItem("High Priority", "High")
        self.render_priority_combo.addItem("Low Priority (Background)", "Low")
        self.render_priority_combo.setToolTip("Select Offline Render Thread Priority")
        self.render_priority_combo.setMinimumWidth(150)
        layout.addWidget(self.render_priority_combo)

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
        
        self.ai_quality_combo.currentDataChanged = lambda: self.ai_quality_changed.emit(self.ai_quality_combo.currentData())
        self.ai_quality_combo.currentIndexChanged.connect(self.ai_quality_combo.currentDataChanged)
        
        self.render_priority_combo.currentDataChanged = lambda: self.render_priority_changed.emit(self.render_priority_combo.currentData())
        self.render_priority_combo.currentIndexChanged.connect(self.render_priority_combo.currentDataChanged)

        # Target Object button -- lives on row 2 with the rest of the
        # interactive object-selection toolset it summons, so row 1's
        # transport/AI combos always have room to show their full text.
        self.target_object_button = QPushButton("🎯 Select Target")
        self.target_object_button.setCheckable(True)
        self.target_object_button.setToolTip("Click to enter interactive point selection mode")
        row2.addWidget(self.target_object_button)

        # Prompt Mode Dropdown
        self.prompt_mode_combo = QComboBox()
        self.prompt_mode_combo.addItem("Stroke Paint", "stroke")
        self.prompt_mode_combo.addItem("Bounding Box", "box")
        self.prompt_mode_combo.setToolTip("Select drawing mode")
        self.prompt_mode_combo.setVisible(False)
        self.prompt_mode_combo.setMinimumWidth(120)
        self.prompt_mode_combo.currentTextChanged.connect(lambda text: self.prompt_mode_changed.emit(self.prompt_mode_combo.currentData()))
        row2.addWidget(self.prompt_mode_combo)

        self.mask_mode_button = QPushButton("Keep (+)")
        self.mask_mode_button.setCheckable(True)
        self.mask_mode_button.setVisible(False)
        self.mask_mode_button.setToolTip("Toggle whether the next stroke adds to or removes from the mask")
        self.mask_mode_button.setStyleSheet("""
            QPushButton { background-color: #2d7d46; color: white; font-weight: bold; border-radius: 4px; padding: 4px; }
            QPushButton:checked { background-color: #cc3333; }
        """)
        self.mask_mode_button.toggled.connect(lambda checked: self.mask_mode_button.setText("Remove (-)" if checked else "Keep (+)"))
        self.mask_mode_button.toggled.connect(lambda checked: self.mask_mode_changed.emit(0 if checked else 1))
        row2.addWidget(self.mask_mode_button)

        self.clear_prompts_button = QPushButton("🗑 Clear")
        self.clear_prompts_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        self.clear_prompts_button.setToolTip("Clear all strokes/points for this object")
        self.clear_prompts_button.setVisible(False)
        row2.addWidget(self.clear_prompts_button)

        self.undo_prompt_button = QPushButton("↩ Undo Last")
        self.undo_prompt_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowBack))
        self.undo_prompt_button.setToolTip("Remove only the most recent stroke/point (Ctrl+Z)")
        self.undo_prompt_button.setVisible(False)
        row2.addWidget(self.undo_prompt_button)

        self.apply_target_button = QPushButton("✓ Apply Target")
        self.apply_target_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        self.apply_target_button.setVisible(False)
        self.apply_target_button.setEnabled(False)
        self.apply_target_button.setStyleSheet("""
            QPushButton { background-color: #2d7d46; color: white; font-weight: bold; border-radius: 4px; padding: 4px 12px; }
            QPushButton:hover { background-color: #3a9d5a; }
        """)
        row2.addWidget(self.apply_target_button)
        row2.addStretch(1)

        # Connect visibility
        def _on_target_object_toggled(checked: bool):
            self.mask_mode_button.setVisible(checked)
            self.prompt_mode_combo.setVisible(checked)
            self.clear_prompts_button.setVisible(checked)
            self.undo_prompt_button.setVisible(checked)
            self.apply_target_button.setVisible(checked)
            self.target_object_button.setText("Cancel" if checked else "🎯 Select Target")
            if checked:
                # Sprint 30: Automatically switch to MobileSAM for interactive tracking
                index = self.ai_mode_combo.findData("sam")
                if index >= 0 and self.ai_mode_combo.currentIndex() != index:
                    self.ai_mode_combo.setCurrentIndex(index)
            else:
                # reset to stroke when toggled off
                self.prompt_mode_combo.setCurrentIndex(0)
                self.mask_mode_button.setChecked(False)

        self.target_object_button.toggled.connect(_on_target_object_toggled)
        
        self.clear_prompts_button.clicked.connect(self.clear_prompts_clicked.emit)
        self.undo_prompt_button.clicked.connect(self.undo_prompt_clicked.emit)
        self.apply_target_button.clicked.connect(self.apply_target_clicked.emit)
        
        self.target_object_button.toggled.connect(self.target_object_toggled.emit)
        self.target_object_button.toggled.connect(
            lambda checked: self.target_object_button.setStyleSheet(
                "QPushButton { background-color: #2d7d46; color: white; }" if checked else ""
            )
        )

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
