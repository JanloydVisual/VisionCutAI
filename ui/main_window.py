from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtGui import QImage, QPixmap

from config import APP_NAME
from core.controller import AppController
from core.gpu_manager import GPUManager
from core.preview_engine import PreviewEngine
from ui.widgets.video_player_widget import VideoPlayerWidget
from ui.widgets.timeline_editor import TimelineEditor


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.controller = AppController()

        self.setWindowTitle(APP_NAME)
        self.resize(1200, 700)

        self.build_ui()
        self.connect_signals()

    # ----------------------------------------------------
    # UI
    # ----------------------------------------------------

    def build_ui(self):

        layout = QVBoxLayout()

        self.file_label = QLabel("No video selected")

        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.open_video)

        top = QHBoxLayout()
        top.addWidget(self.file_label)
        top.addStretch()
        top.addWidget(self.browse_button)

        self.video_player = VideoPlayerWidget()

        self.timeline_editor = TimelineEditor()
        self.timeline_editor.set_project(self.controller.project)

        gpu = GPUManager.get_gpu_info()

        gpu_text = (
            f"GPU : {gpu['name']}"
            if gpu["available"]
            else "GPU : Not Available"
        )

        self.gpu_label = QLabel(gpu_text)

        self.remove_button = QPushButton("Remove Background")
        self.remove_button.setEnabled(False)

        layout.addLayout(top)
        layout.addWidget(self.video_player)
        layout.addWidget(self.timeline_editor)
        layout.addWidget(self.gpu_label)
        layout.addWidget(self.remove_button)

        container = QWidget()
        container.setLayout(layout)

        self.setCentralWidget(container)

    # ----------------------------------------------------
    # Signals
    # ----------------------------------------------------

    def connect_signals(self):

        self.video_player.play_clicked.connect(self.controller.play)
        self.video_player.pause_clicked.connect(self.controller.pause)
        self.video_player.stop_clicked.connect(self.controller.stop)

        self.video_player.next_frame_clicked.connect(self.controller.next_frame)
        self.video_player.previous_frame_clicked.connect(self.controller.previous_frame)
        self.video_player.frame_scrubbed.connect(self.controller.seek)

        engine = self.controller.video

        engine.video_loaded.connect(self.video_loaded)
        engine.frame_ready.connect(self.update_preview)

        self.controller.processing.frame_processed.connect(self.update_processed_frame)

    # ----------------------------------------------------
    # Video
    # ----------------------------------------------------

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

            self.timeline_editor.update()

    def video_loaded(self, info):

        self.video_player.set_video_info(
            f"Loaded | "
            f"{info['Width']} x {info['Height']} | "
            f"{info['FPS']:.2f} FPS"
        )

        self.video_player.set_controls_enabled(True)
        self.video_player.set_total_frames(info["Frames"], info["FPS"])
        self.remove_button.setEnabled(True)

    def update_preview(self, frame):

        pixmap = PreviewEngine.frame_to_pixmap(frame)
        self.video_player.load_frame(pixmap)

        self.video_player.set_current_frame(
            self.controller.video.current_frame_index
        )

    def update_processed_frame(self, frame):
        """
        Receives frames from ProcessingEngine. The AI processor
        returns RGBA (4-channel); the default PassthroughProcessor
        (fallback if AI deps are missing) returns 3-channel BGR.
        Handled locally here rather than modifying PreviewEngine,
        since its current contents/usages elsewhere are unknown.
        """
        pixmap = self._frame_to_pixmap(frame)
        self.video_player.set_processed_frame(pixmap)

    @staticmethod
    def _frame_to_pixmap(frame):
        if frame.ndim == 3 and frame.shape[2] == 4:
            h, w, _ = frame.shape
            image = QImage(
                frame.data, w, h, w * 4, QImage.Format.Format_RGBA8888
            ).copy()
            return QPixmap.fromImage(image)

        return PreviewEngine.frame_to_pixmap(frame)

    # ----------------------------------------------------
    # Shutdown
    # ----------------------------------------------------

    def closeEvent(self, event):
        self.controller.release()
        super().closeEvent(event)
