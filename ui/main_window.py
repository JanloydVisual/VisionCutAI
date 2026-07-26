from PyQt6.QtWidgets import (
    QToolBar,
    QDockWidget, QProgressBar,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
    QMenuBar,
    QMenu,
    QStackedWidget,
)
from PyQt6.QtGui import QImage, QPixmap, QKeySequence, QShortcut, QDropEvent, QAction
from PyQt6.QtCore import Qt, QSettings, QUrl, QTimer, QVariantAnimation, QEasingCurve, QAbstractAnimation
import os
import sys
import cv2
import subprocess

from config import APP_NAME
from core.controller import AppController
from core.gpu_manager import GPUManager
from core.preview_engine import PreviewEngine
from ui.widgets.video_player_widget import VideoPlayerWidget
from ui.widgets.timeline_editor import TimelineEditor
from ui.engine_bridge import ProcessingBridge
from ui.widgets.export_panel import ExportPanel, COLLAPSED_WIDTH as EXPORT_PANEL_COLLAPSED_WIDTH, EXPANDED_WIDTH as EXPORT_PANEL_EXPANDED_WIDTH
from ui.export_bridge import ExportBridge
from ui.export_progress_dialog import ExportProgressDialog
from ui.export_complete_dialog import ExportCompleteDialog
from ui.cancel_export_dialog import CancelExportDialog
from ui.widgets.developer_panel import DeveloperPanel
from ui.welcome_screen import WelcomeScreen
from ui.widgets.stage_indicator import StageIndicator
from ui.widgets.prompt_list_panel import PromptListPanel


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

    def __init__(self, is_dev=False):
        super().__init__()
        self.is_dev = is_dev

        self.settings = QSettings(APP_NAME, APP_NAME)

        self.controller = AppController()
        self.processing_bridge = ProcessingBridge(self.controller.processing)
        self._processed_frames_received = 0
        self._last_original_shape = None
        self.preview_scale = 1.0

        title = APP_NAME
        if getattr(self, 'is_dev', False):
            title += " [DEV]"
        self.setWindowTitle(title)
        
        self.resize(1200, 700)
        self.setMinimumSize(900, 600)
        
        self.setAcceptDrops(True)
        self._current_media_path = None

        self.export_bridge = ExportBridge(self.controller.exporter, self)
        self.export_bridge.export_started.connect(self._on_export_started)
        self.export_bridge.export_progress.connect(self._on_export_progress)
        self.export_bridge.export_finished.connect(self._on_export_finished)
        self.export_bridge.export_error.connect(self._on_export_error)
        self.export_bridge.export_cancelled.connect(self._on_export_cancelled)

        self.build_ui()
        self.build_menus()

        self.connect_signals()
        self.setup_shortcuts()
        
        # Auto-save Timer
        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self._perform_autosave)
        self.autosave_timer.start(300000)  # 5 minutes

    def build_ui(self):
        # 1. Top Toolbar (Grouped)
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)
        
        # Workspace Section
        self.toolbar.addWidget(QLabel(" Workspace: "))
        self.file_label = QLabel("No media selected")
        self.toolbar.addWidget(self.file_label)
        
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.open_media)
        self.toolbar.addWidget(self.browse_button)
        
        self.horizontal_workspace_button = QPushButton("Horizontal")
        self.vertical_workspace_button = QPushButton("Vertical")
        self.horizontal_workspace_button.clicked.connect(lambda: self.set_workspace_mode("horizontal"))
        self.vertical_workspace_button.clicked.connect(lambda: self.set_workspace_mode("vertical"))
        self.toolbar.addWidget(self.horizontal_workspace_button)
        self.toolbar.addWidget(self.vertical_workspace_button)
        
        self.toolbar.addSeparator()
        
        # AI Section
        self.toolbar.addWidget(QLabel(" AI: "))
        self.ai_quality_combo = QComboBox()
        self.ai_quality_combo.addItems(["Draft", "Balanced", "Best"])
        self.ai_quality_combo.setCurrentText("Balanced")
        self.ai_quality_combo.currentTextChanged.connect(self._on_ai_quality_changed)
        self.toolbar.addWidget(self.ai_quality_combo)
        
        self.toolbar.addSeparator()
        
        # View Section
        self.toolbar.addWidget(QLabel(" View: "))
        self.preview_quality_combo = QComboBox()
        self.preview_quality_combo.addItems(["Full Resolution", "Half Resolution", "Quarter Resolution"])
        self.preview_quality_combo.currentTextChanged.connect(self._on_preview_quality_changed)
        self.toolbar.addWidget(self.preview_quality_combo)
        
        self.export_panel_toggle_button = QPushButton("📤 Export")
        self.export_panel_toggle_button.setCheckable(True)
        self.toolbar.addWidget(self.export_panel_toggle_button)
        
        self.timeline_toggle_button = QPushButton("🎬 Timeline")
        self.timeline_toggle_button.setCheckable(True)
        self.timeline_toggle_button.setChecked(True)
        self.toolbar.addWidget(self.timeline_toggle_button)
        
        if self.is_dev:
            self.dev_panel_toggle_button = QPushButton("🛠 Developer")
            self.dev_panel_toggle_button.setCheckable(True)
            self.dev_panel_toggle_button.setChecked(True)
            self.toolbar.addWidget(self.dev_panel_toggle_button)
            
        self.stage_indicator = StageIndicator()
        
        # 2. Central Widget (Viewer + Stage Indicator)
        self.video_player = VideoPlayerWidget()
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.addWidget(self.stage_indicator)
        center_layout.addWidget(self.video_player, stretch=1)
        
        # 3. Dock Panels
        self.setDockOptions(QMainWindow.DockOption.AllowNestedDocks | QMainWindow.DockOption.AnimatedDocks)
        
        # Left Dock: Prompt List Panel (Object/AI)
        self.prompt_list_panel = PromptListPanel(self)
        self.prompt_list_dock = QDockWidget("Objects & AI", self)
        self.prompt_list_dock.setWidget(self.prompt_list_panel)
        self.prompt_list_dock.setObjectName("PromptListDock")
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.prompt_list_dock)
        self.prompt_list_dock.setVisible(False)
        
        # Right Dock: Export Panel
        self.export_panel = ExportPanel(self)
        self.export_dock = QDockWidget("Export", self)
        self.export_dock.setWidget(self.export_panel)
        self.export_dock.setObjectName("ExportDock")
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.export_dock)
        self.export_panel.export_requested.connect(self._on_export_requested)
        self.export_panel.collapsed_changed.connect(self._on_export_panel_collapsed_changed)
        self.export_panel_toggle_button.clicked.connect(
            lambda: self.export_dock.setVisible(not self.export_dock.isVisible()))
            
        # Bottom Dock: Timeline
        self.timeline_editor = TimelineEditor()
        self.timeline_editor.set_project(self.controller.project)
        self.timeline_editor.set_render_cache(self.controller.render_cache)
        self.timeline_editor.collapsed_changed.connect(self._on_timeline_collapsed_changed)
        
        self.timeline_dock = QDockWidget("Timeline", self)
        self.timeline_dock.setWidget(self.timeline_editor)
        self.timeline_dock.setObjectName("TimelineDock")
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.timeline_dock)
        self.timeline_toggle_button.clicked.connect(
            lambda: self.timeline_dock.setVisible(not self.timeline_dock.isVisible()))

        # Status Bar
        self.status = self.statusBar()
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status.addPermanentWidget(self.progress_bar)
        
        self.lbl_proj = QLabel("Project: Ready")
        self.lbl_video = QLabel("Video: None")
        self.ai_status_label = QLabel("Cache: 0 | AI: Idle")
        self.tracking_status_label = QLabel("Tracking: Idle")
        self.lbl_gpu = QLabel("GPU: -")
        self.lbl_vram = QLabel("VRAM: -")
        self.lbl_ram = QLabel("RAM: -")
        
        for lbl in (self.lbl_proj, self.lbl_video, self.ai_status_label, self.tracking_status_label, self.lbl_gpu, self.lbl_vram, self.lbl_ram):
            self.status.addWidget(lbl)
            
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._update_status_bar)
        self.status_timer.start(1000)

        # Welcome Screen and Stack
        self.welcome_screen = WelcomeScreen()
        self.welcome_screen.open_project_requested.connect(self.open_media)
        self.welcome_screen.import_video_requested.connect(self.open_media)
        
        self.main_stack = QStackedWidget()
        self.main_stack.addWidget(self.welcome_screen)
        self.main_stack.addWidget(center_widget)
        
        self.setCentralWidget(self.main_stack)
        
        # Load Workspace Persistence
        self.load_workspace_layout()

    def load_workspace_layout(self):
        settings = QSettings("VisionCutAI", "Workspace")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        state = settings.value("windowState")
        if state:
            self.restoreState(state)

    def closeEvent(self, event):
        settings = QSettings("VisionCutAI", "Workspace")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        super().closeEvent(event)

    def _on_preview_quality_changed(self, text: str):
        if text == "Full Resolution":
            self.preview_scale = 1.0
        elif text == "Half Resolution":
            self.preview_scale = 0.5
        elif text == "Quarter Resolution":
            self.preview_scale = 0.25
        
        if self.controller.video.is_loaded and not self.controller.video.is_playing:
            self.controller.video.seek(self.controller.video.current_frame_index)

    def _on_ai_quality_changed(self, text: str):
        """Pass the user's selected AI processing quality to the controller."""
        self.controller.set_ai_preview_quality(text)

    def build_menus(self):
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("File")
        action_open = QAction("Open Project/Video...", self)
        action_open.triggered.connect(self.open_media)
        file_menu.addAction(action_open)
        
        file_menu.addSeparator()
        
        action_settings = QAction("Settings...", self)
        action_settings.triggered.connect(self.open_settings)
        file_menu.addAction(action_settings)
        
        file_menu.addSeparator()
        action_exit = QAction("Exit", self)
        action_exit.triggered.connect(self.close)
        file_menu.addAction(action_exit)

        help_menu = menubar.addMenu("Help")
        action_about = QAction("About VisionCut AI", self)
        action_about.triggered.connect(self.open_about)
        help_menu.addAction(action_about)
        
        if self.is_dev:
            dev_menu = menubar.addMenu("Developer")
    
            action_restart = QAction("Restart Application", self)
            action_restart.triggered.connect(self._dev_restart_app)
            dev_menu.addAction(action_restart)
    
            action_clear = QAction("Clear Render Cache", self)
            action_clear.triggered.connect(self._dev_clear_cache)
            dev_menu.addAction(action_clear)
    
            action_test = QAction("Run Integration Tests", self)
            action_test.triggered.connect(self._dev_run_tests)
            dev_menu.addAction(action_test)
    
            action_bench = QAction("Performance Benchmark", self)
            action_bench.triggered.connect(self._dev_run_benchmark)
            dev_menu.addAction(action_bench)
    
            action_logs = QAction("Open Logs Directory", self)
            action_logs.triggered.connect(self._dev_open_logs)
            dev_menu.addAction(action_logs)

    def open_settings(self):
        from ui.settings_dialog import SettingsDialog
        dlg = SettingsDialog(self)
        dlg.exec()
        
    def open_about(self):
        from ui.about_dialog import AboutDialog
        dlg = AboutDialog(self)
        dlg.exec()

    def _dev_restart_app(self):
        os.execl(sys.executable, sys.executable, *sys.argv)

    def _dev_clear_cache(self):
        self.controller.render_cache.clear()

    def _dev_run_tests(self):
        subprocess.Popen(["cmd.exe", "/c", "start", "pytest"])

    def _dev_run_benchmark(self):
        subprocess.Popen(["cmd.exe", "/c", "start", "python", "scratch/benchmark_cache.py"])

    def _dev_open_logs(self):
        os.makedirs("logs", exist_ok=True)
        os.startfile("logs")

    def _perform_autosave(self):
        if hasattr(self.controller, 'project'):
            import datetime
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            os.makedirs("autosave", exist_ok=True)
            with open(f"autosave/checkpoint_{timestamp}.json", "w") as f:
                f.write('{"status": "auto-saved"}')

    def _update_status_bar(self):
        import psutil
        import subprocess
        
        if self.controller.video.is_loaded:
            fps = getattr(self.controller.video, 'fps', 0)
            w = getattr(self.controller.video.decoder, 'width', 0) if hasattr(self.controller.video, 'decoder') and self.controller.video.decoder else 0
            h = getattr(self.controller.video.decoder, 'height', 0) if hasattr(self.controller.video, 'decoder') and self.controller.video.decoder else 0
            self.lbl_video.setText(f"Video: {w}x{h} | {fps:.1f} FPS")
        else:
            self.lbl_video.setText("Video: None")
            
        if hasattr(self.controller, 'render_cache') and self.controller.render_cache:
            try:
                frames = len(list(self.controller.render_cache.cache_dir.glob("*.png")))
                ai_text = getattr(self.controller, 'background_removal_status', 'Idle')
                self.ai_status_label.setText(f"Cache: {frames} | AI: {ai_text}")
            except:
                pass
                
        try:
            res = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader,nounits"],
                encoding="utf-8", stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW
            ).strip()
            if res:
                parts = res.split(",")
                if len(parts) >= 2:
                    self.lbl_gpu.setText(f"GPU: {parts[0].strip()}%")
                    self.lbl_vram.setText(f"VRAM: {parts[1].strip()} MB")
        except:
            pass
            
        mem = psutil.virtual_memory()
        self.lbl_ram.setText(f"RAM: {mem.used / (1024*1024*1024):.1f} GB")

    def set_workspace_mode(self, mode: str):
        if not hasattr(self, 'timeline_dock'): return
        if mode == "vertical":
            self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.timeline_dock)
            self.workspace_mode = "vertical"
        else:
            self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.timeline_dock)
            self.workspace_mode = "horizontal"
        self.settings.setValue("workspace_mode", self.workspace_mode)
        self.video_player.fit_to_window()

    def connect_signals(self):
        self.video_player.play_clicked.connect(self.controller.play)
        self.video_player.pause_clicked.connect(self.controller.pause)
        self.video_player.stop_clicked.connect(self.controller.stop)
        self.video_player.remove_bg_clicked.connect(self.toggle_remove_bg)
        self.video_player.ai_mode_changed.connect(self.controller.set_ai_mode)
        
        self.video_player.ai_quality_changed.connect(self.controller.set_ai_preview_quality)
        self.video_player.render_priority_changed.connect(self.controller.render_cache.set_render_priority)
        self.video_player.target_object_toggled.connect(self.controller.set_drawing_mode)
        self.video_player.target_object_toggled.connect(self.prompt_list_panel.setVisible)
        self.video_player.target_object_selected.connect(self.controller.set_target_object)
        self.video_player.target_object_live_updated.connect(self.controller.set_target_object_live)

        # New connections for interactive paint mask
        self.controller.on_interactive_mask_updated = self.video_player.set_interactive_mask
        self.controller.on_interactive_points_updated = self.video_player.set_interactive_points
        self.controller.on_interactive_busy_changed = self.video_player.set_interactive_busy
        self.controller.on_tracker_initialized = self._update_ai_status_ui
        self.controller.on_error_occurred = self._show_error_dialog
        self.controller.on_tracking_progress_updated = self._on_tracking_progress
        self.controller.on_tracking_status_changed = self._on_tracking_status
        self.controller.on_render_cache_started = self._on_render_cache_started
        self.controller.on_workflow_stage_changed = self.stage_indicator.set_active_stage
        self.controller.on_prompt_list_changed = self._on_prompt_list_changed

        self.video_player.clear_prompts_clicked.connect(self.controller.clear_target_prompts)
        self.video_player.undo_prompt_clicked.connect(self.controller.undo_target_prompt)
        self.video_player.apply_target_clicked.connect(self.controller.apply_target)

        # Sprint 36: Prompt List panel actions -- select is pure UI (no
        # controller call needed), the rest change the prompt list and so
        # go through the controller, whose on_prompt_list_changed callback
        # above refreshes this same panel afterward.
        self.prompt_list_panel.prompt_toggled.connect(self.controller.toggle_prompt_enabled)
        self.prompt_list_panel.prompt_deleted.connect(self.controller.delete_prompt)
        self.prompt_list_panel.undo_requested.connect(self.controller.undo_target_prompt)
        self.prompt_list_panel.redo_requested.connect(self.controller.redo_target_prompt)

        self.video_player.next_frame_clicked.connect(self.controller.next_frame)
        self.video_player.previous_frame_clicked.connect(self.controller.previous_frame)
        self.video_player.frame_scrubbed.connect(self.controller.seek)

        self._connect_timeline_signals()

    def _show_error_dialog(self, message: str):
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(self, "AI Processing Error", message)

    def _connect_timeline_signals(self):
        self.timeline_editor.seek_requested.connect(self.controller.seek)
        self.timeline_editor.clip_selected.connect(self.select_timeline_clip)
        self.timeline_editor.clip_move_requested.connect(self.move_timeline_clip)
        self.timeline_editor.clip_trim_requested.connect(self.trim_timeline_clip)
        self.timeline_editor.split_requested.connect(self.split_timeline_clip)
        self.timeline_editor.delete_requested.connect(self.delete_timeline_clip)

        # Extended timeline and professional editing signals
        self.timeline_editor.clip_edit_started.connect(self.controller.begin_timeline_edit)
        self.timeline_editor.clip_edit_finished.connect(self.finish_timeline_edit)
        self.timeline_editor.link_toggle_requested.connect(self.toggle_link_timeline_clip)
        self.timeline_editor.render_preview_requested.connect(self.start_render_cache)
        self.timeline_editor.split_at_frame.connect(self._on_split_at_frame)
        self.timeline_editor.playhead_dragged.connect(self._on_playhead_dragged)
        self.timeline_editor.blade_preview_frame.connect(self._on_blade_preview_frame)

        # Controller and bridge signals
        self.controller.frame_ready.connect(self.update_preview)
        self.controller.video.video_loaded.connect(self.video_loaded)
        self.processing_bridge.frame_processed.connect(self.update_processed_frame)
        self.processing_bridge.telemetry_updated.connect(self.update_telemetry)

    def _on_tracking_progress(self, current, total, confidence):
        self.tracking_status_label.setText(f"Tracking Object... Frame {current} / {total} | Confidence: {int(confidence * 100)}%")
        self.tracking_status_label.setStyleSheet("color: #FFC107; font-size: 11px; font-weight: bold;") # Amber while tracking

    def _on_tracking_status(self, text):
        self.tracking_status_label.setText(f"Tracking: {text}")
        # Sprint 35: "Refinement: Regressed ..." must not fall through to
        # the green default below -- check it before the generic
        # "Partial object detected" amber branch since a regression can
        # legitimately follow either a clean or a partial result.
        if "Refinement: Regressed" in text:
            self.tracking_status_label.setStyleSheet("color: #F44336; font-size: 11px; font-weight: bold;") # Red -- this prompt made it worse
        elif "Refinement: Improved" in text:
            self.tracking_status_label.setStyleSheet("color: #4CAF50; font-size: 11px; font-weight: bold;") # Green -- this prompt helped
        elif "Refinement: Stayed the same" in text:
            self.tracking_status_label.setStyleSheet("color: #5dade2; font-size: 11px; font-weight: bold;") # Neutral blue -- no change
        elif "Failed" in text or "Lost" in text or "Paused" in text or "No object detected" in text:
            self.tracking_status_label.setStyleSheet("color: #F44336; font-size: 11px; font-weight: bold;") # Red for errors
        elif "Partial object detected" in text:
            self.tracking_status_label.setStyleSheet("color: #FFB300; font-size: 11px; font-weight: bold;") # Amber warning, not a success
        elif "Complete" in text:
            self.tracking_status_label.setStyleSheet("color: #4CAF50; font-size: 11px; font-weight: bold;") # Green for success
        else:
            self.tracking_status_label.setStyleSheet("color: #4CAF50; font-size: 11px; font-weight: bold;")

    def _on_prompt_list_changed(self):
        """Sprint 36: fired after any prompt-list edit (add/delete/toggle/
        undo/redo) -- simplest correct approach is to just rebuild the
        panel from the controller's current state rather than trying to
        patch it incrementally."""
        self.prompt_list_panel.refresh(
            self.controller._interactive_prompts,
            self.controller._last_refinement_verdict,
        )

    def _on_split_at_frame(self, timeline_frame: int) -> None:
        """Blade tool: split clip at the clicked timeline position."""
        if self.controller.split_at_position(timeline_frame):
            self.timeline_editor.refresh()
            self.video_player.set_status(f"Clip split at frame {timeline_frame}")

    def _on_playhead_dragged(self, timeline_frame: int) -> None:
        """Dragging the red playhead line."""
        self.controller.seek(timeline_frame)

    def _on_blade_preview_frame(self, timeline_frame: int) -> None:
        """Blade mode hover: preview seek without moving playhead."""
        self.controller.preview_seek(timeline_frame)

    def setup_shortcuts(self):
        self.undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        self.redo_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Z"), self)
        self.delete_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Delete), self)
        self.backspace_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Backspace), self)
        self.esc_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)

        self.undo_shortcut.activated.connect(self.undo_timeline)
        self.redo_shortcut.activated.connect(self.redo_timeline)
        self.delete_shortcut.activated.connect(self.delete_timeline_clip)
        self.backspace_shortcut.activated.connect(self.delete_timeline_clip)
        self.esc_shortcut.activated.connect(self.cancel_interactive_mask)

        # -- Global keyboard playback controls (JKL / Space / B) --------
        # Space: toggle play/pause
        self.space_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        self.space_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.space_shortcut.activated.connect(self._toggle_playback)

        # J: reverse playback (cycle speed: -1x â†’ -2x â†’ -4x)
        self.j_shortcut = QShortcut(QKeySequence(Qt.Key.Key_J), self)
        self.j_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.j_shortcut.activated.connect(self._increase_reverse_speed)

        # K: pause and play (toggle, reset speed to 1x if starting to play)
        self.k_shortcut = QShortcut(QKeySequence(Qt.Key.Key_K), self)
        self.k_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.k_shortcut.activated.connect(self._toggle_playback_and_reset_speed)

        # L: forward playback (cycle speed: 1x â†’ 2x â†’ 4x)
        self.l_shortcut = QShortcut(QKeySequence(Qt.Key.Key_L), self)
        self.l_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.l_shortcut.activated.connect(self._increase_forward_speed)

        # B: toggle blade mode
        self.b_shortcut = QShortcut(QKeySequence(Qt.Key.Key_B), self)
        self.b_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.b_shortcut.activated.connect(self._toggle_blade_mode)

        # Added in Sprint 21
        QShortcut(QKeySequence(Qt.Key.Key_Left), self, activated=self.controller.previous_frame)
        QShortcut(QKeySequence(Qt.Key.Key_Right), self, activated=self.controller.next_frame)
        QShortcut(QKeySequence(Qt.Key.Key_Home), self, activated=lambda: self.controller.seek(0))
        QShortcut(QKeySequence(Qt.Key.Key_End), self, activated=lambda: self.controller.seek(self.controller.video.total_frames - 1) if self.controller.video.is_loaded else None)
        
        QShortcut(QKeySequence("Ctrl+I"), self, activated=self.open_media)
        QShortcut(QKeySequence("Ctrl+E"), self, activated=self.export_panel.export_btn.click)
        QShortcut(QKeySequence("Ctrl+B"), self, activated=lambda: self._on_split_at_frame(self.controller.video.current_frame_index))
        
        QShortcut(QKeySequence("Shift+Z"), self, activated=self.video_player.fit_to_window)

    # -- Playback helpers ------------------------------------------------

    def _toggle_playback(self):
        self.controller.toggle_playback()

    def _toggle_playback_and_reset_speed(self):
        """K key: toggle play/pause and reset speed to 1x."""
        if self.controller.timeline_playback.is_playing:
            self.controller.pause()
        else:
            self.controller.reset_playback_speed()
            self.controller.play()

    def _increase_forward_speed(self):
        """L key: cycle forward speed 1x â†’ 2x â†’ 4x."""
        self.controller.increase_forward_speed()

    def _increase_reverse_speed(self):
        """J key: cycle reverse speed -1x â†’ -2x â†’ -4x."""
        self.controller.increase_reverse_speed()


    def _toggle_blade_mode(self):
        """B key: toggle blade mode on/off."""
        enabled = self.controller.toggle_blade_mode()
        self.timeline_editor.set_blade_mode(enabled)
        if enabled:
            self.video_player.set_status("Blade Mode")
        else:
            self.video_player.set_status("Selection Mode")

    def dragEnterEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            url = event.mimeData().urls()[0]
            if url.isLocalFile():
                ext = os.path.splitext(url.toLocalFile())[1].lower()
                if ext in [".mp4", ".mov", ".avi", ".png", ".jpg", ".webp"]:
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        url = event.mimeData().urls()[0]
        filepath = url.toLocalFile()
        self.open_media(filepath)

    def open_media(self, filepath=None):
        if not filepath:
            filepath, _ = QFileDialog.getOpenFileName(
                self,
                "Open Media",
                "",
                "Media (*.mp4 *.mov *.avi *.png *.jpg *.webp)"
            )

        if not filepath:
            return

        self.main_stack.setCurrentIndex(1)
        
        self._current_media_path = filepath
        ext = os.path.splitext(filepath)[1].lower()

        if ext in [".png", ".jpg", ".webp"]:
            info = self.controller.open_image(filepath)
            if info:
                self.file_label.setText(filepath)
                self.image_loaded(info)
                self.export_panel.update_output_name(filepath)
        else:
            success = self.controller.open_video(filepath)
            if success:
                self.file_label.setText(filepath)
                self.timeline_editor.refresh()
                self._update_link_button_state()
                self.export_panel.update_output_name(filepath)
                # Sprint 34.1: timeline_editor.refresh() above resizes the
                # canvas/header to match the loaded project's real content,
                # which silently triggers Qt to recompute the splitter's
                # layout and override the ~70/30 split set_workspace_mode()
                # just applied inside video_loaded() (QSplitter.setSizes()
                # is a one-time command, not a persistent constraint, and
                # a child's size-hint change can force a relayout that
                # ignores it). Reapply now that all content-driven sizing
                # has settled, so the viewer's share actually sticks.
                self.set_workspace_mode(self.workspace_mode)

    def image_loaded(self, info):
        self.video_player.set_video_info(
            f"Loaded Image | {info['Width']} x {info['Height']}"
        )
        self.video_player.set_controls_enabled(False)
        self.timeline_editor.parent().hide()
        
        img = self.controller.get_loaded_image()
        if img is not None:
            self.update_preview(img, 0)
            
        self._update_ai_status_ui()
        self.export_panel.format_combo.setCurrentText("PNG (Image)")

    def video_loaded(self, info):
        # Portrait sources (common for social/vertical content) get squashed
        # to a sliver if left in the wide/short "horizontal" pane -- match
        # the workspace layout to the footage so the preview is actually
        # usable without the user having to discover the toggle themselves.
        best_mode = "vertical" if info['Height'] > info['Width'] else "horizontal"
        if getattr(self, "workspace_mode", None) != best_mode:
            self.set_workspace_mode(best_mode)

        self.video_player.set_video_info(
            f"Loaded | {info['Width']} x {info['Height']} | "
            f"{info['FPS']:.2f} FPS"
        )

        self.video_player.set_controls_enabled(True)
        self.timeline_editor.parent().show()
        self.video_player.set_total_frames(info["Frames"], info["FPS"])
        self.timeline_editor.set_fps(info["FPS"])

        self._update_ai_status_ui()
        self.export_panel.format_combo.setCurrentText("MOV Alpha")
        self._apply_workspace_proportions()

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_workspace_proportions()

    def _apply_workspace_proportions(self):
        if not hasattr(self, 'timeline_dock'):
            return
            
        h = self.height()
        if not self.controller.video.is_loaded:
            # EMPTY: Viewer 85% Timeline 15%
            self.resizeDocks([self.timeline_dock], [int(h * 0.15)], Qt.Orientation.Vertical)
        else:
            # MEDIA: Viewer 70% Timeline 30%
            self.resizeDocks([self.timeline_dock], [int(h * 0.30)], Qt.Orientation.Vertical)

    def _update_ai_status_ui(self):
        if self.controller.is_background_removal_active:
            self.video_player.set_remove_bg_text("Stop Background Removal")
            self.video_player.set_remove_bg_enabled(True)
        elif self.controller.background_removal_available:
            if not self.controller.object_tracker.is_tracking:
                self.video_player.set_remove_bg_text("Remove Background (Needs Target)")
                self.video_player.set_remove_bg_enabled(False)
            else:
                self.video_player.set_remove_bg_text("Remove Background")
                self.video_player.set_remove_bg_enabled(True)
        else:
            self.video_player.set_remove_bg_text("Background Removal Unavailable")
            self.video_player.set_remove_bg_enabled(False)
            
        self._update_status_bar()

    def toggle_remove_bg(self):
        self.controller.toggle_background_removal()
        
        if not self.controller.is_background_removal_active:
            # clear the processed preview and revert to original
            self.video_player.show_original_preview()
            self._processed_frames_received = 0
            self.controller.frames_sent_to_processing = 0
        
        # update the UI buttons and labels
        self._update_ai_status_ui()

    # --- Export Slots ---
    def _on_export_requested(self, output_dir, output_name, output_format):
        if not self._current_media_path:
            return

        if output_format == "PNG (Image)":
            self.controller.exporter.export_image(self._current_media_path, output_dir, output_name)
        else:
            self.controller.exporter.start_export(
                self._current_media_path, output_dir, 
                output_name=output_name, output_format=output_format
            )

    def _on_export_started(self, output_dir):
        format_str = self.export_panel.get_output_format()
        is_video = format_str in ["Transparent WebM", "MOV Alpha"]
        self.progress_dialog = ExportProgressDialog(self, is_video=is_video)
        self.progress_dialog.cancelled.connect(self.controller.exporter.cancel_export)
        self.progress_dialog.show()

    def _on_export_progress(self, current, total):
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.set_progress(current, total)

    def _on_export_finished(self, output_dir):
        if hasattr(self, 'progress_dialog') and self.progress_dialog is not None:
            try:
                self.progress_dialog.accept()
            except RuntimeError:
                pass
            self.progress_dialog = None

        dialog = ExportCompleteDialog(self, output_path=output_dir)
        dialog.exec()
        # Sprint 34.2: "Do not automatically collapse panels -- the user
        # decides." -- Sprint 34.1 auto-collapsed the export panel here;
        # that's now the user's call via the toolbar toggle.

    def _on_export_error(self, error_msg):
        if hasattr(self, 'progress_dialog') and self.progress_dialog is not None:
            try:
                self.progress_dialog.reject()
            except RuntimeError:
                pass
            self.progress_dialog = None
        self.video_player.set_status(f"Export Error: {error_msg}")
        # Sprint 34.2: no auto-collapse -- see _on_export_finished.

    def _on_export_cancelled(self, output_dir, frames_exported):
        self.video_player.set_status(f"Export Cancelled (saved {frames_exported} frames)")
        # Sprint 34.2: no auto-collapse -- see _on_export_finished.

    # ------------------------------------------------------------------
    # Sprint 34.2: Toggleable panels (Export / Timeline / Developer)
    # ------------------------------------------------------------------

    def _animate_splitter_to(self, splitter: QSplitter, target_sizes: list, duration: int = 220) -> None:
        """Smoothly interpolate a QSplitter's pane sizes from wherever
        they currently are to target_sizes. Reused for both the export
        panel (main_splitter) and the timeline collapse (self.splitter) --
        QSplitter has no built-in animated setSizes(), so this steps it
        via QVariantAnimation instead.
        """
        start_sizes = list(splitter.sizes())
        if len(start_sizes) != len(target_sizes):
            splitter.setSizes(target_sizes)
            return

        anim = QVariantAnimation(self)
        anim.setDuration(duration)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

        def step(t):
            sizes = [int(a + (b - a) * t) for a, b in zip(start_sizes, target_sizes)]
            splitter.setSizes(sizes)
        anim.valueChanged.connect(step)

        if not hasattr(self, '_panel_animations'):
            self._panel_animations = []
        self._panel_animations.append(anim)
        anim.finished.connect(lambda: self._panel_animations.remove(anim) if anim in self._panel_animations else None)
        anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)

    def _on_export_panel_collapsed_changed(self, collapsed: bool) -> None:
        # Sprint 34.1: viewer-first -- give the freed/reclaimed width to the
        # viewer+timeline side of the main splitter, not just to the panel
        # itself, so expanding/collapsing actually changes usable preview
        # space rather than leaving dead space.
        # Sprint 34.2: animated, remembers the pre-collapse width instead
        # of always snapping back to a fixed default, and persists state.
        total = sum(self.main_splitter.sizes()) or (1160 + EXPORT_PANEL_EXPANDED_WIDTH)
        if collapsed:
            current_width = self.main_splitter.sizes()[1]
            if current_width > EXPORT_PANEL_COLLAPSED_WIDTH + 10:
                self._export_panel_prev_width = current_width
            target_width = EXPORT_PANEL_COLLAPSED_WIDTH
        else:
            target_width = getattr(self, '_export_panel_prev_width', EXPORT_PANEL_EXPANDED_WIDTH)
        self._animate_splitter_to(self.main_splitter, [max(total - target_width, 200), target_width])
        self.export_panel_toggle_button.setChecked(not collapsed)
        self.settings.setValue("export_panel_collapsed", collapsed)

    def _timeline_pane_index(self) -> int:
        # self.splitter's child order swaps between workspace modes (see
        # set_workspace_mode) -- horizontal: [video, timeline], vertical:
        # [timeline, video]. Anything sizing the timeline pane specifically
        # needs to know which index it's actually at right now.
        return 0 if getattr(self, 'workspace_mode', 'horizontal') == 'vertical' else 1

    def _on_timeline_collapsed_changed(self, collapsed: bool) -> None:
        idx = self._timeline_pane_index()
        video_idx = 1 - idx
        sizes = list(self.splitter.sizes())
        total = sum(sizes) or 1000
        if collapsed:
            if sizes[idx] > 50:
                self._timeline_prev_size = sizes[idx]
            target_timeline = 40
        else:
            target_timeline = getattr(self, '_timeline_prev_size', 300)
        new_sizes = [0, 0]
        new_sizes[idx] = target_timeline
        new_sizes[video_idx] = max(total - target_timeline, 200)
        self._animate_splitter_to(self.splitter, new_sizes)
        self.timeline_toggle_button.setChecked(not collapsed)
        self.settings.setValue("timeline_collapsed", collapsed)

    def _on_dev_panel_toggle_clicked(self) -> None:
        self.dev_panel.setVisible(not self.dev_panel.isVisible())

    def _on_dev_panel_visibility_changed(self, visible: bool) -> None:
        # Also fires if the user closes the dock via its own [x] or
        # re-docks/floats it -- keeps the toolbar button and QSettings in
        # sync regardless of which control the user actually used. Skipped
        # during window teardown (see closeEvent) since Qt hides the dock
        # as a side effect of closing, which is not a user preference change.
        if getattr(self, '_closing', False):
            return
        self.dev_panel_toggle_button.setChecked(visible)
        self.settings.setValue("dev_panel_visible", visible)

    def _restore_panel_states(self) -> None:
        export_collapsed = self.settings.value("export_panel_collapsed", True, type=bool)
        self.export_panel.set_collapsed(export_collapsed)
        # set_collapsed() no-ops if the value already matches its
        # construction-time default (True) -- force the splitter sizing
        # and button state to apply regardless, so a persisted "expanded"
        # actually shows expanded on this launch too.
        self._on_export_panel_collapsed_changed(export_collapsed)

        timeline_collapsed = self.settings.value("timeline_collapsed", False, type=bool)
        self.timeline_editor.set_collapsed(timeline_collapsed)
        self._on_timeline_collapsed_changed(timeline_collapsed)

        if self.is_dev:
            dev_visible = self.settings.value("dev_panel_visible", True, type=bool)
            self.dev_panel.setVisible(dev_visible)
            self.dev_panel_toggle_button.setChecked(dev_visible)

    def start_background_removal(self):
        if not self.controller.start_background_removal():
            self.video_player.set_status(
                self.controller.background_removal_status
            )
            return

        self.video_player.show_processed_preview()
        self.video_player.set_remove_bg_text("Background Removal Active")
        self.video_player.set_remove_bg_enabled(False)
        self._update_status_bar()
        self.video_player.set_status("AI processing started")

    def select_timeline_clip(self, clip):
        if self.controller.select_clip(clip):
            self.timeline_editor.refresh()
            self._update_link_button_state()

    def _update_link_button_state(self):
        clip = self.controller.selected_clip()
        is_linked = getattr(clip, 'linked_id', None) is not None if clip else False
        self.timeline_editor.update_link_button_state(is_linked)

    def toggle_link_timeline_clip(self):
        if self.controller.toggle_link_selected_clip():
            self.timeline_editor.refresh()
            self._update_link_button_state()
            self.video_player.set_status("Clip link state toggled")

    def _on_render_cache_started(self, worker):
        from ui.export_progress_dialog import ExportProgressDialog
        self.render_dialog = ExportProgressDialog(self)
        self.render_dialog.setWindowTitle("Generating AI Cache...")
        self.render_dialog.cancelled.connect(self.cancel_render_cache)
        
        worker.progress_updated.connect(self.render_dialog.set_progress)
        worker.finished.connect(self.render_cache_finished)
        
        self.render_dialog.show()
        worker.start()

    def start_render_cache(self):
        if not self.controller.project.timeline.clips:
            self.video_player.set_status("Timeline is empty")
            return
            
        self.controller.pause()
        
        from ui.export_progress_dialog import ExportProgressDialog
        self.render_dialog = ExportProgressDialog(self)
        self.render_dialog.setWindowTitle("Rendering Preview Cache...")
        self.render_dialog.cancelled.connect(self.cancel_render_cache)
        
        worker = self.controller.render_cache.start_caching(
            self.controller.timeline_playback,
            self.controller.tracking_engine,
            processor=self.controller._background_removal_processor
        )
        worker.progress_updated.connect(self.render_dialog.set_progress)
        worker.finished.connect(self.render_cache_finished)
        
        self.render_dialog.show()
        worker.start()

    def cancel_render_cache(self):
        self.controller.render_cache.cancel()
        if hasattr(self, 'render_dialog') and self.render_dialog:
            self.render_dialog.close()

    def render_cache_finished(self, success, message):
        if hasattr(self, 'render_dialog') and self.render_dialog:
            self.render_dialog.close()
        
        self.timeline_editor.refresh()
        
        if success:
            self.video_player.set_status("Render Cache Complete - Playback is now perfectly smooth")
            self.controller.preview_seek(self.controller.timeline_playback.current_timeline_frame)
        else:
            self.video_player.set_status(f"Render Cache stopped: {message}")

    def move_timeline_clip(self, clip, timeline_start_frame):
        if self.controller.move_clip(clip, timeline_start_frame):
            self.timeline_editor.refresh()

    def trim_timeline_clip(self, clip, edge, timeline_frame):
        if self.controller.trim_clip(clip, edge, timeline_frame):
            self.timeline_editor.refresh()

    def split_timeline_clip(self):
        if self.controller.split_selected_clip_at_playhead():
            self.timeline_editor.refresh()
            self._update_link_button_state()
            self.video_player.set_status("Clip split at playhead")
        else:
            self.video_player.set_status("Select a clip and place the playhead inside it")

    def delete_timeline_clip(self):
        if self.controller.delete_selected_clip():
            self.timeline_editor.refresh()
            self._update_link_button_state()
            self.video_player.set_status("Selected clip deleted")
        else:
            self.video_player.set_status("No selected clip to delete")

    def finish_timeline_edit(self):
        if self.controller.end_timeline_edit():
            self.timeline_editor.refresh()

    def cancel_interactive_mask(self):
        if self.video_player.controls.target_object_button.isChecked():
            self.video_player.controls.target_object_button.setChecked(False)

    def undo_timeline(self):
        if self.video_player.controls.target_object_button.isChecked():
            self.controller.undo_target_prompt()
            return
            
        if self.controller.undo_timeline():
            self.timeline_editor.refresh()
            self._update_link_button_state()
            self.video_player.set_status("Timeline edit undone")

    def redo_timeline(self):
        if self.video_player.controls.target_object_button.isChecked():
            self.controller.redo_target_prompt()
            return
            
        if self.controller.redo_timeline():
            self.timeline_editor.refresh()
            self._update_link_button_state()
            self.video_player.set_status("Timeline edit redone")

    def update_preview(self, frame, timeline_frame):
        self._last_original_shape = tuple(frame.shape)
        
        if self.preview_scale < 1.0:
            h, w = frame.shape[:2]
            new_w, new_h = int(w * self.preview_scale), int(h * self.preview_scale)
            frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
            
        pixmap = self._frame_to_pixmap(frame)
        self.video_player.load_frame(pixmap, self.preview_scale)

        # Fetch cached frame if it exists
        cached_frame = self.controller.render_cache.get_composite(timeline_frame, frame)
        if cached_frame is not None:
            # Resize if needed
            if self.preview_scale < 1.0:
                h, w = cached_frame.shape[:2]
                new_w, new_h = int(w * self.preview_scale), int(h * self.preview_scale)
                cached_frame = cv2.resize(cached_frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
            cached_pixmap = self._frame_to_pixmap(cached_frame)
            self.video_player.set_processed_frame(cached_pixmap, self.preview_scale)
        else:
            # Fallback to the raw frame if not cached, so the video doesn't freeze or jump
            self.video_player.set_processed_frame(pixmap, self.preview_scale)

        self.video_player.set_current_frame(timeline_frame)
        self.timeline_editor.set_playhead_frame(timeline_frame)

    def update_processed_frame(self, frame):
        # Ignore out-of-order asynchronous AI frames if we are actively playing
        if self.controller.timeline_playback.is_playing:
            return
            
        self._processed_frames_received += 1
        output_shape = tuple(frame.shape)

        if self.preview_scale < 1.0:
            h, w = frame.shape[:2]
            new_w, new_h = int(w * self.preview_scale), int(h * self.preview_scale)
            display_frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
        else:
            display_frame = frame

        pixmap = self._frame_to_pixmap(display_frame)
        self.video_player.set_processed_frame(pixmap, self.preview_scale)

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

    def update_telemetry(self, data):
        self._update_status_bar()

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
        # Sprint 34.2: closing the window hides the Developer Panel dock as
        # a side effect, which fires visibilityChanged(False) -- without
        # this flag, _on_dev_panel_visibility_changed would mistake that
        # for a real user toggle and silently overwrite their actual
        # preference with "hidden" on every single exit.
        self._closing = True
        self.controller.release()
        super().closeEvent(event)
