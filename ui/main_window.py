from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtGui import QImage, QPixmap, QKeySequence, QShortcut
from PyQt6.QtCore import Qt

from config import APP_NAME
from core.controller import AppController
from core.gpu_manager import GPUManager
from core.preview_engine import PreviewEngine
from ui.widgets.video_player_widget import VideoPlayerWidget
from ui.widgets.timeline_editor import TimelineEditor
from ui.engine_bridge import ProcessingBridge


SPLITTER_STYLE = """
QSplitter::handle {
    background-color: #444;
    height: 3px;
    margin: 0;
}
QSplitter::handle:hover {
    background-color: #2d7d46;
}
QSplitter::handle:pressed {
    background-color: #3a9d5a;
}
"""


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.controller = AppController()
        self.processing_bridge = ProcessingBridge(self.controller.processing)
        self._processed_frames_received = 0
        self._last_original_shape = None

        self.setWindowTitle(APP_NAME)
        self.resize(1200, 700)

        self.build_ui()
        self.connect_signals()
        self.setup_shortcuts()

    def build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # -- Top bar (file label + browse) --
        top_bar = QWidget()
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(8, 4, 8, 4)
        self.file_label = QLabel("No video selected")
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.open_video)
        top_layout.addWidget(self.file_label)
        top_layout.addStretch()
        top_layout.addWidget(self.browse_button)
        layout.addWidget(top_bar)

        # -- Vertical splitter: preview (top) / timeline + info (bottom) --
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setHandleWidth(8)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setStyleSheet(SPLITTER_STYLE)

        # Top section: video player (preview + controls + scrub bar)
        self.video_player = VideoPlayerWidget()
        self.splitter.addWidget(self.video_player)

        # Bottom section: timeline editor + status info
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(2)

        self.timeline_editor = TimelineEditor()
        self.timeline_editor.set_project(self.controller.project)
        bottom_layout.addWidget(self.timeline_editor, stretch=1)

        # Status bar below timeline
        status_bar = QHBoxLayout()
        status_bar.setContentsMargins(8, 2, 8, 4)

        gpu = GPUManager.get_gpu_info()
        gpu_text = (
            f"GPU : {gpu['name']}"
            if gpu["available"]
            else "GPU : Not Available"
        )
        self.gpu_label = QLabel(gpu_text)
        self.gpu_label.setStyleSheet("color: #888; font-size: 11px;")

        self.ai_status_label = QLabel(self.controller.background_removal_status)
        self.ai_status_label.setWordWrap(True)
        self.ai_status_label.setStyleSheet("color: #888; font-size: 11px;")

        status_bar.addWidget(self.gpu_label)
        status_bar.addWidget(self.ai_status_label)
        status_bar.addStretch()

        bottom_layout.addLayout(status_bar)

        self.splitter.addWidget(bottom_widget)

        # Initial 70/30 split
        self.splitter.setSizes([490, 210])

        layout.addWidget(self.splitter, stretch=1)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def connect_signals(self):
        self.video_player.play_clicked.connect(self.controller.play)
        self.video_player.pause_clicked.connect(self.controller.pause)
        self.video_player.stop_clicked.connect(self.controller.stop)
        self.video_player.remove_bg_clicked.connect(self.start_background_removal)

        self.video_player.next_frame_clicked.connect(self.controller.next_frame)
        self.video_player.previous_frame_clicked.connect(self.controller.previous_frame)
        self.video_player.frame_scrubbed.connect(self.controller.seek)

        self.timeline_editor.seek_requested.connect(self.controller.seek)
        self.timeline_editor.clip_selected.connect(self.select_timeline_clip)
        self.timeline_editor.clip_move_requested.connect(self.move_timeline_clip)
        self.timeline_editor.clip_trim_requested.connect(self.trim_timeline_clip)
        self.timeline_editor.split_requested.connect(self.split_timeline_clip)
        self.timeline_editor.delete_requested.connect(self.delete_timeline_clip)
        self.timeline_editor.clip_edit_started.connect(
            self.controller.begin_timeline_edit
        )
        self.timeline_editor.clip_edit_finished.connect(
            self.finish_timeline_edit
        )

        # Professional editing signals
        self.timeline_editor.split_at_frame.connect(self._on_split_at_frame)
        self.timeline_editor.playhead_dragged.connect(self._on_playhead_dragged)

        # Connect to the coordinator's signal which emits
        # (frame, timeline_frame) instead of raw source frames.
        self.controller.frame_ready.connect(self.update_preview)

        # VideoEngine.video_loaded is still the source-of-truth for
        # metadata after a file is opened.
        self.controller.video.video_loaded.connect(self.video_loaded)

        self.processing_bridge.frame_processed.connect(self.update_processed_frame)

    def _on_split_at_frame(self, timeline_frame: int) -> None:
        """Blade tool: split clip at the clicked timeline position."""
        if self.controller.split_at_position(timeline_frame):
            self.timeline_editor.refresh()
            self.video_player.set_status(f"Clip split at frame {timeline_frame}")

    def _on_playhead_dragged(self, timeline_frame: int) -> None:
        """Dragging the red playhead line."""
        self.controller.seek(timeline_frame)

    def setup_shortcuts(self):
        self.undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        self.redo_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Z"), self)
        self.delete_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Delete), self)
        self.backspace_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Backspace), self)

        self.undo_shortcut.activated.connect(self.undo_timeline)
        self.redo_shortcut.activated.connect(self.redo_timeline)
        self.delete_shortcut.activated.connect(self.delete_timeline_clip)
        self.backspace_shortcut.activated.connect(self.delete_timeline_clip)

        # -- Global keyboard playback controls (JKL / Space / B) --------
        # Space: toggle play/pause
        self.space_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        self.space_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.space_shortcut.activated.connect(self._toggle_playback)

        # J: reverse playback (cycle speed: -1x → -2x → -4x)
        self.j_shortcut = QShortcut(QKeySequence(Qt.Key.Key_J), self)
        self.j_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.j_shortcut.activated.connect(self._increase_reverse_speed)

        # K: pause + reset speed to 1x
        self.k_shortcut = QShortcut(QKeySequence(Qt.Key.Key_K), self)
        self.k_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.k_shortcut.activated.connect(self._pause_and_reset_speed)

        # L: forward playback (cycle speed: 1x → 2x → 4x)
        self.l_shortcut = QShortcut(QKeySequence(Qt.Key.Key_L), self)
        self.l_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.l_shortcut.activated.connect(self._increase_forward_speed)

        # B: toggle blade mode
        self.b_shortcut = QShortcut(QKeySequence(Qt.Key.Key_B), self)
        self.b_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.b_shortcut.activated.connect(self._toggle_blade_mode)

    # -- Playback helpers ------------------------------------------------

    def _toggle_playback(self):
        self.controller.toggle_playback()

    def _increase_forward_speed(self):
        """L key: cycle forward speed 1x → 2x → 4x."""
        self.controller.increase_forward_speed()

    def _increase_reverse_speed(self):
        """J key: cycle reverse speed -1x → -2x → -4x."""
        self.controller.increase_reverse_speed()

    def _pause_and_reset_speed(self):
        """K key: pause and reset speed to 1x."""
        self.controller.pause()
        self.controller.reset_playback_speed()

    def _toggle_blade_mode(self):
        """B key: toggle blade mode on/off."""
        enabled = self.controller.toggle_blade_mode()
        self.timeline_editor.set_blade_mode(enabled)
        if enabled:
            self.video_player.set_status("Blade Mode")
        else:
            self.video_player.set_status("Selection Mode")

    def open_video(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open Video",
            "",
            "Videos (*.mp4 *.mov *.avi)"
        )

        if not filename:
            return

        success = self.controller.open_video(filename)

        if success:
            self.file_label.setText(filename)
            self.timeline_editor.refresh()

    def video_loaded(self, info):
        self.video_player.set_video_info(
            f"Loaded | {info['Width']} x {info['Height']} | "
            f"{info['FPS']:.2f} FPS"
        )

        self.video_player.set_controls_enabled(True)
        self.video_player.set_total_frames(info["Frames"], info["FPS"])
        self.timeline_editor.set_fps(info["FPS"])

        if self.controller.background_removal_active:
            self.video_player.set_remove_bg_text("Background Removal Active")
            self.video_player.set_remove_bg_enabled(False)
            self.ai_status_label.setText("Background removal active")
        elif self.controller.background_removal_available:
            self.video_player.set_remove_bg_text("Remove Background")
            self.video_player.set_remove_bg_enabled(True)
            self.ai_status_label.setText(self.controller.background_removal_status)
        else:
            self.video_player.set_remove_bg_text("Background Removal Unavailable")
            self.video_player.set_remove_bg_enabled(False)
            self.ai_status_label.setText(self.controller.background_removal_status)

    def start_background_removal(self):
        if not self.controller.start_background_removal():
            self.video_player.set_status(
                self.controller.background_removal_status
            )
            return

        self.video_player.show_processed_preview()
        self.video_player.set_remove_bg_text("Background Removal Active")
        self.video_player.set_remove_bg_enabled(False)
        self.ai_status_label.setText("Background removal active ? processed preview is full-screen")
        self.video_player.set_status("AI processing started")

    def select_timeline_clip(self, clip):
        if self.controller.select_clip(clip):
            self.timeline_editor.refresh()

    def move_timeline_clip(self, clip, timeline_start_frame):
        if self.controller.move_clip(clip, timeline_start_frame):
            self.timeline_editor.refresh()

    def trim_timeline_clip(self, clip, edge, timeline_frame):
        if self.controller.trim_clip(clip, edge, timeline_frame):
            self.timeline_editor.refresh()

    def split_timeline_clip(self):
        if self.controller.split_selected_clip_at_playhead():
            self.timeline_editor.refresh()
            self.video_player.set_status("Clip split at playhead")
        else:
            self.video_player.set_status("Select a clip and place the playhead inside it")

    def delete_timeline_clip(self):
        if self.controller.delete_selected_clip():
            self.timeline_editor.refresh()
            self.video_player.set_status("Selected clip deleted")
        else:
            self.video_player.set_status("No selected clip to delete")

    def finish_timeline_edit(self):
        if self.controller.end_timeline_edit():
            self.timeline_editor.refresh()

    def undo_timeline(self):
        if self.controller.undo_timeline():
            self.timeline_editor.refresh()
            self.video_player.set_status("Timeline edit undone")

    def redo_timeline(self):
        if self.controller.redo_timeline():
            self.timeline_editor.refresh()
            self.video_player.set_status("Timeline edit redone")

    def update_preview(self, frame, timeline_frame):
        self._last_original_shape = tuple(frame.shape)
        pixmap = PreviewEngine.frame_to_pixmap(frame)
        self.video_player.load_frame(pixmap)

        self.video_player.set_current_frame(timeline_frame)
        self.timeline_editor.set_playhead_frame(timeline_frame)

    def update_processed_frame(self, frame):
        self._processed_frames_received += 1

        pixmap = self._frame_to_pixmap(frame)
        self.video_player.set_processed_frame(pixmap)

        output_shape = tuple(frame.shape)
        alpha_status = "no alpha channel"

        if frame.ndim == 3 and frame.shape[2] == 4:
            alpha = frame[:, :, 3]
            transparent_pixels = int((alpha < 250).sum())
            alpha_status = (
                f"alpha {int(alpha.min())}-{int(alpha.max())}, "
                f"transparent pixels: {transparent_pixels}"
            )

        if self._processed_frames_received <= 3 or self._processed_frames_received % 15 == 0:
            self.video_player.set_status(
                "AI preview | "
                f"sent: {self.controller.frames_sent_to_processing} | "
                f"received: {self._processed_frames_received} | "
                f"input: {self._last_original_shape} | "
                f"output: {output_shape} | {alpha_status}"
            )

    @staticmethod
    def _frame_to_pixmap(frame):
        if frame.ndim == 3 and frame.shape[2] == 4:
            h, w, _ = frame.shape
            image = QImage(
                frame.data, w, h, w * 4, QImage.Format.Format_RGBA8888
            ).copy()
            return QPixmap.fromImage(image)

        return PreviewEngine.frame_to_pixmap(frame)

    def closeEvent(self, event):
        self.controller.release()
        super().closeEvent(event)