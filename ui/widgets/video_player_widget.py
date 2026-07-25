"""
VideoPlayerWidget
------------------
Composes the center editing surface:
    VideoPreview      (zoom/pan viewer + overlay + comparison)
    PlaybackControls  (Play/Pause/Stop)
    TimelineWidget    (scrub bar, step buttons, position display)

This class arranges children and re-exposes what MainWindow needs.
It holds NO business logic and never imports core/ or ai/.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QPixmap

from ui.widgets.video_preview import VideoPreview
from ui.widgets.playback_controls import PlaybackControls
from ui.widgets.timeline_widget import TimelineWidget


class VideoPlayerWidget(QWidget):
    play_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    remove_bg_clicked = pyqtSignal()
    frame_scrubbed = pyqtSignal(int)
    next_frame_clicked = pyqtSignal()
    previous_frame_clicked = pyqtSignal()
    ai_mode_changed = pyqtSignal(str)
    ai_quality_changed = pyqtSignal(str)
    render_priority_changed = pyqtSignal(str)
    
    target_object_toggled = pyqtSignal(bool)
    prompt_mode_changed = pyqtSignal(str)
    target_object_selected = pyqtSignal(dict)
    target_object_live_updated = pyqtSignal(dict)
    clear_prompts_clicked = pyqtSignal()
    undo_prompt_clicked = pyqtSignal()
    apply_target_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # Sprint 34.1: TimelineEditor (the other pane sharing a QSplitter
        # with this widget) explicitly claims Expanding horizontally; this
        # widget defaulted to Preferred, so Qt's layout kept re-equalizing
        # the split on any relayout regardless of the splitter's
        # setSizes()/stretch factors -- Expanding vs Preferred isn't a fair
        # fight, and Expanding tends to win extra space. Matching it here
        # lets the splitter's explicit ratio actually govern the split.
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.preview = VideoPreview()
        layout.addWidget(self.preview, stretch=1)

        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.info_label)

        self.status_label = QLabel("Idle")
        self.status_label.setStyleSheet("color: #aaa;")
        layout.addWidget(self.status_label)

        self.controls = PlaybackControls()
        self.controls.set_controls_enabled(False)
        layout.addWidget(self.controls)

        self.timeline = TimelineWidget()
        layout.addWidget(self.timeline)

        self.controls.play_clicked.connect(self.play_clicked.emit)
        self.controls.pause_clicked.connect(self.pause_clicked.emit)
        self.controls.stop_clicked.connect(self.stop_clicked.emit)
        self.controls.remove_bg_clicked.connect(self.remove_bg_clicked.emit)
        self.controls.ai_mode_changed.connect(self.ai_mode_changed.emit)
        self.controls.ai_quality_changed.connect(self.ai_quality_changed.emit)
        self.controls.render_priority_changed.connect(self.render_priority_changed.emit)
        
        self.controls.target_object_toggled.connect(self.target_object_toggled.emit)
        self.controls.target_object_toggled.connect(self.preview.set_drawing_mode)
        self.controls.mask_mode_changed.connect(self.preview.set_mask_mode)
        self.controls.prompt_mode_changed.connect(self.prompt_mode_changed.emit)
        self.controls.prompt_mode_changed.connect(self.preview.set_prompt_mode)
        
        self.controls.clear_prompts_clicked.connect(self.clear_prompts_clicked.emit)
        self.controls.undo_prompt_clicked.connect(self.undo_prompt_clicked.emit)
        self.controls.apply_target_clicked.connect(self.apply_target_clicked.emit)
        
        self.preview.target_object_selected.connect(self.target_object_selected.emit)
        self.preview.target_object_live_updated.connect(self.target_object_live_updated.emit)

        self.timeline.frame_scrubbed.connect(self.frame_scrubbed.emit)
        self.timeline.next_frame_clicked.connect(self.next_frame_clicked.emit)
        self.timeline.previous_frame_clicked.connect(self.previous_frame_clicked.emit)

    # ---------------- Public API ----------------
    def set_interactive_mask(self, mask, is_low_confidence: bool = False):
        self.preview.set_interactive_mask(mask, is_low_confidence)

    def set_interactive_points(self, points):
        self.preview.viewer.set_interactive_points(points)
        self._has_interactive_points = len(points) > 0
        self._update_apply_target_enabled()

    def set_interactive_busy(self, busy: bool) -> None:
        """A regenerate is in flight on the background worker -- disable
        Apply Target so a stale mask can't be committed mid-update."""
        self._interactive_busy = busy
        self._update_apply_target_enabled()

    def set_debug_prompt_points(self, points) -> None:
        self.preview.viewer.set_debug_prompt_points(points)

    def set_debug_layer_visible(self, layer: str, visible: bool) -> None:
        self.preview.viewer.set_debug_layer_visible(layer, visible)

    def _update_apply_target_enabled(self) -> None:
        has_points = getattr(self, '_has_interactive_points', False)
        busy = getattr(self, '_interactive_busy', False)
        self.controls.apply_target_button.setEnabled(has_points and not busy)

    def load_frame(self, pixmap: QPixmap, scale_factor: float = 1.0) -> None:
        self.preview.load_frame(pixmap, scale_factor)

    def set_processed_frame(self, pixmap: QPixmap, scale_factor: float = 1.0) -> None:
        self.preview.set_processed_frame(pixmap, scale_factor)

    def show_processed_preview(self) -> None:
        self.preview.show_processed_preview()

    def show_original_preview(self) -> None:
        self.preview.show_original_preview()

    def clear(self) -> None:
        self.preview.clear()
        self.status_label.setText("Idle")
        self.info_label.setText("")

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def set_remove_bg_enabled(self, enabled: bool) -> None:
        self.controls.set_remove_bg_enabled(enabled)

    def set_remove_bg_text(self, text: str) -> None:
        self.controls.set_remove_bg_text(text)

    def set_video_info(self, info: str) -> None:
        self.info_label.setText(info)

    def set_controls_enabled(self, enabled: bool) -> None:
         self.controls.set_controls_enabled(enabled)

    def set_total_frames(self, total_frames: int, fps: float) -> None:
        self.timeline.set_total_frames(total_frames, fps)

    def set_current_frame(self, frame_index: int) -> None:
        self.timeline.set_current_frame(frame_index)

    def fit_to_window(self) -> None:
        self.preview.fit_to_window()

    def get_overlay_widget(self):
        return self.preview.get_overlay()

    def get_timeline_widget(self) -> TimelineWidget:
        return self.timeline
