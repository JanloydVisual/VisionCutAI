from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QAbstractScrollArea,
    QPushButton,
    QLabel,
    QSizePolicy,
)
from PyQt6.QtCore import pyqtSignal

from ui.widgets.timeline.timeline_canvas import (
    TimelineCanvas,
    TRACK_LABEL_WIDTH,
    PIXELS_PER_FRAME,
)
from ui.widgets.timeline.timeline_ruler import TimelineRuler
from ui.widgets.timeline.track_header import TrackHeaderColumn

# Purely visual gap between TrackHeaderColumn and the scrollable canvas.
# This never touches frame/pixel math - it only widens the layout spacer
# so the ruler stays lined up with the canvas it labels.
HEADER_CANVAS_MARGIN = 6


class TimelineEditor(QWidget):
    seek_requested = pyqtSignal(int)
    split_requested = pyqtSignal()
    delete_requested = pyqtSignal()
    link_toggle_requested = pyqtSignal()
    render_preview_requested = pyqtSignal()
    clip_selected = pyqtSignal(object)
    clip_move_requested = pyqtSignal(object, int)
    clip_trim_requested = pyqtSignal(object, str, int)
    clip_edit_started = pyqtSignal()
    clip_edit_finished = pyqtSignal()
    split_at_frame = pyqtSignal(int)
    playhead_dragged = pyqtSignal(int)
    blade_preview_frame = pyqtSignal(int)
    collapsed_changed = pyqtSignal(bool)

    AUTO_SCROLL_MARGIN = 40

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project = None
        self.zoom_factor = 1.0
        self._collapsed = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)

        toolbar = QHBoxLayout()
        self.split_button = QPushButton("Split at Playhead")
        self.delete_button = QPushButton("Delete Selected")
        self.link_toggle_button = QPushButton("Unlink")
        self.render_preview_button = QPushButton("Render Preview")
        self.render_preview_button.setStyleSheet("font-weight: bold; color: #4CAF50;")

        toolbar.addWidget(self.split_button)
        toolbar.addWidget(self.delete_button)
        toolbar.addWidget(self.link_toggle_button)
        toolbar.addWidget(self.render_preview_button)
        toolbar.addWidget(QLabel("Drag clips to move - drag yellow edges to trim"))
        toolbar.addStretch(1)
        # Sprint 34.2: wrapped in a container so set_collapsed() can hide
        # the whole toolbar as one unit (a bare QHBoxLayout has no
        # setVisible() of its own).
        self.toolbar_container = QWidget()
        self.toolbar_container.setLayout(toolbar)
        root.addWidget(self.toolbar_container)

        # Ruler row: a spacer matches the header column width so the
        # ruler's time markings line up with the scrollable canvas,
        # not the fixed header.
        ruler_row = QHBoxLayout()
        ruler_row.setContentsMargins(0, 0, 0, 0)
        ruler_row.setSpacing(0)
        ruler_spacer = QWidget()
        ruler_spacer.setFixedWidth(TRACK_LABEL_WIDTH + HEADER_CANVAS_MARGIN)
        self.ruler = TimelineRuler()
        ruler_row.addWidget(ruler_spacer)
        ruler_row.addWidget(self.ruler)
        root.addLayout(ruler_row)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self.header = TrackHeaderColumn()

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(False)
        self.scroll.setMinimumWidth(200)
        self.scroll.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustIgnored)

        self.canvas = TimelineCanvas()
        self.scroll.setWidget(self.canvas)

        body.addWidget(self.header)

        margin_spacer = QWidget()
        margin_spacer.setFixedWidth(HEADER_CANVAS_MARGIN)
        body.addWidget(margin_spacer)

        self.scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        # Sane initial default before any project/tracks are loaded;
        # _sync_scroll_height() overrides this once track data exists.
        self.scroll.setFixedHeight(170)

        body.addWidget(self.scroll)

        # Sprint 34.2: same reasoning as toolbar_container above -- lets
        # the collapsed view hide tracks/clips as one unit and show just
        # the ruler row (added separately, above, and never hidden).
        self.body_container = QWidget()
        self.body_container.setLayout(body)
        root.addWidget(self.body_container)

        self.scroll.horizontalScrollBar().valueChanged.connect(
            self.ruler.set_scroll_offset
        )

        self.scroll.horizontalScrollBar().valueChanged.connect(
            self.canvas.set_scroll_offset
        )

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMinimumHeight(90)
        # Sprint 34.1: without an explicit minimum width, Qt falls back to
        # minimumSizeHint(), which -- despite the canvas living inside a
        # QScrollArea specifically so its width can be decoupled from
        # content width -- was still bubbling up toward the canvas's own
        # 4000px+ minimum (TimelineCanvas._sync_content_width()), silently
        # flooring this pane at ~650px and defeating any narrower split
        # requested for the "vertical" (portrait-video) workspace mode.
        # The scroll area's own horizontal scrollbar is exactly what makes
        # a genuinely narrow allocation here fine.
        self.setMinimumWidth(220)

        self.split_button.clicked.connect(self.split_requested.emit)
        self.delete_button.clicked.connect(self.delete_requested.emit)
        self.link_toggle_button.clicked.connect(self.link_toggle_requested.emit)
        self.render_preview_button.clicked.connect(self.render_preview_requested.emit)

        self.ruler.seek_requested.connect(self.seek_requested.emit)
        self.ruler.playhead_dragged.connect(self.playhead_dragged.emit)
        
        self.canvas.ruler_clicked.connect(self.seek_requested.emit)
        self.canvas.clip_selected.connect(self.clip_selected.emit)
        self.canvas.clip_move_requested.connect(self.clip_move_requested.emit)
        self.canvas.clip_trim_requested.connect(self.clip_trim_requested.emit)
        self.canvas.clip_edit_started.connect(self.clip_edit_started.emit)
        self.canvas.clip_edit_finished.connect(self.clip_edit_finished.emit)
        self.canvas.split_at_frame.connect(self.split_at_frame.emit)
        self.canvas.blade_preview_frame.connect(self.blade_preview_frame.emit)

    def set_project(self, project):
        self.project = project
        if project:
            self.canvas.set_timeline(project.timeline)
            self.header.set_timeline(project.timeline)
            self._sync_scroll_height()

    def set_render_cache(self, render_cache):
        self.ruler.set_render_cache(render_cache)

    def _sync_scroll_height(self):
        # Keep the scroll viewport matched to the canvas's real content
        # height (which now scales with track count) plus a small strip
        # for the horizontal scrollbar, instead of a fixed magic number.
        self.scroll.setFixedHeight(self.canvas.height() + 20)

    def set_fps(self, fps):
        self.canvas.set_fps(fps)
        self.ruler.set_fps(fps)

    def refresh(self):
        self.canvas.refresh()
        self.header.update()
        
    def update_link_button_state(self, is_linked: bool):
        if is_linked:
            self.link_toggle_button.setText("Unlink")
        else:
            self.link_toggle_button.setText("Link")

    def set_blade_mode(self, enabled: bool) -> None:
        self.canvas.set_blade_mode(enabled)

    def is_collapsed(self) -> bool:
        return self._collapsed

    def set_collapsed(self, collapsed: bool) -> None:
        """Sprint 34.2: collapsed shows only the ruler + playhead row --
        the toolbar (Split/Delete/Unlink/Render Preview) and the full
        track/clip body are hidden as two units. Height constraints are
        adjusted here too so the outer splitter actually has room to
        shrink this pane; MainWindow drives the animated resize itself
        via the collapsed_changed signal, same pattern as ExportPanel.
        """
        if self._collapsed == collapsed:
            return
        self._collapsed = collapsed
        self.toolbar_container.setVisible(not collapsed)
        self.body_container.setVisible(not collapsed)
        if collapsed:
            self.setMinimumHeight(36)
            self.setMaximumHeight(44)
        else:
            self.setMinimumHeight(90)
            self.setMaximumHeight(16777215)
        self.collapsed_changed.emit(collapsed)

    def set_playhead_frame(self, frame_index):
        self.canvas.set_playhead_frame(frame_index)
        self.ruler.set_playhead_frame(frame_index)
        if getattr(self.ruler, '_dragging_playhead', False):
            return
        self._auto_scroll_to_playhead(frame_index)

    def _auto_scroll_to_playhead(self, frame_index):
        playhead_x = frame_index * (2 * self.zoom_factor)

        bar = self.scroll.horizontalScrollBar()
        viewport_width = self.scroll.viewport().width()
        visible_left = bar.value()
        visible_right = visible_left + viewport_width

        if playhead_x < visible_left + self.AUTO_SCROLL_MARGIN:
            bar.setValue(int(max(0, playhead_x - self.AUTO_SCROLL_MARGIN)))
        elif playhead_x > visible_right - self.AUTO_SCROLL_MARGIN:
            bar.setValue(int(playhead_x - viewport_width + self.AUTO_SCROLL_MARGIN))

    def set_zoom(self, zoom: float):
        self.zoom_factor = max(0.5, min(5.0, zoom))
        
        import ui.widgets.timeline.timeline_canvas as tc
        import ui.widgets.timeline.timeline_ruler as tr
        
        scaled_ppf = 2 * self.zoom_factor
        tc.PIXELS_PER_FRAME = scaled_ppf
        tr.PIXELS_PER_FRAME = scaled_ppf
        
        if self.project:
            self.canvas._sync_content_width()
            self.refresh()
            self._auto_scroll_to_playhead(self.canvas.playhead_frame)

    def wheelEvent(self, event):
        from PyQt6.QtCore import Qt
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            
            bar = self.scroll.horizontalScrollBar()
            viewport_width = self.scroll.viewport().width()
            
            center_frame = (bar.value() + viewport_width / 2.0) / (2 * self.zoom_factor)
            
            if delta > 0:
                self.set_zoom(self.zoom_factor * 1.25)
            elif delta < 0:
                self.set_zoom(self.zoom_factor / 1.25)
                
            new_center_x = center_frame * (2 * self.zoom_factor)
            bar.setValue(int(max(0, new_center_x - viewport_width / 2.0)))
            
            event.accept()
        else:
            super().wheelEvent(event)
