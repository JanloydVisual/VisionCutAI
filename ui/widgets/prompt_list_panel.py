"""
PromptListPanel
----------------
Sprint 36: Interactive Prompt Editing. Shows every Keep(+)/Remove(-)
prompt in the current selection -- in order, with its position and when
it was added -- and lets the user select, enable/disable, delete, or
undo/redo any of them, instead of only ever being able to undo the most
recently added stroke.

Pure UI: reads controller state and emits signals: never calls SAM or
touches the mask itself, that belongs to the controller.
"""

import time

from PyQt6.QtWidgets import (
    QDockWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QCheckBox,
)
from PyQt6.QtCore import Qt, pyqtSignal


def _describe_prompt(p: dict) -> str:
    ptype = p.get('type')
    if ptype == 'stroke':
        pts = p.get('data') or []
        n = len(pts)
        if n >= 2:
            return f"stroke, {n} pts  ({pts[0][0]},{pts[0][1]}) → ({pts[-1][0]},{pts[-1][1]})"
        if n == 1:
            return f"stroke, 1 pt  ({pts[0][0]},{pts[0][1]})"
        return "stroke, 0 pts"
    if ptype == 'point':
        x, y = p.get('data', [0, 0])
        return f"point  ({x},{y})"
    if ptype == 'rectangle':
        x1, y1, x2, y2 = p.get('data', [0, 0, 0, 0])
        return f"box  ({x1},{y1})–({x2},{y2})"
    return ptype or "prompt"


class PromptRowWidget(QWidget):
    toggled = pyqtSignal(int, bool)
    delete_clicked = pyqtSignal(int)

    def __init__(self, prompt: dict, parent=None):
        super().__init__(parent)
        self.prompt_id = prompt.get('id')

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(8)

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(prompt.get('enabled', True))
        self.checkbox.setToolTip("Enable/disable this prompt (kept, just excluded from SAM)")
        self.checkbox.toggled.connect(lambda checked: self.toggled.emit(self.prompt_id, checked))
        layout.addWidget(self.checkbox)

        label = prompt.get('label', 1)
        kind = "Keep (+)" if label == 1 else "Remove (-)"
        kind_color = "#4CAF50" if label == 1 else "#F44336"

        order = prompt.get('order', 0) + 1
        desc = _describe_prompt(prompt)
        ts = prompt.get('timestamp')
        ts_str = time.strftime("%H:%M:%S", time.localtime(ts)) if ts else "-"

        text = QLabel(f"<b>#{order}</b> <span style='color:{kind_color};'>{kind}</span> — {desc}  <span style='color:#888;'>{ts_str}</span>")
        text.setStyleSheet("font-size: 11px; color: #ddd;")
        layout.addWidget(text, stretch=1)

        self.delete_button = QPushButton("✕")
        self.delete_button.setFixedWidth(24)
        self.delete_button.setToolTip("Delete this prompt")
        self.delete_button.setStyleSheet("QPushButton { color: #F44336; border: none; font-weight: bold; }")
        self.delete_button.clicked.connect(lambda: self.delete_clicked.emit(self.prompt_id))
        layout.addWidget(self.delete_button)

        if not prompt.get('enabled', True):
            self.setStyleSheet("background-color: rgba(255,255,255,10);")
            text.setStyleSheet("font-size: 11px; color: #777;")


class PromptListPanel(QDockWidget):
    prompt_selected = pyqtSignal(int)
    prompt_toggled = pyqtSignal(int, bool)
    prompt_deleted = pyqtSignal(int)
    undo_requested = pyqtSignal()
    redo_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("Prompt List", parent)
        self.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        self.lbl_counts = QLabel("Prompts: 0 total, 0 active")
        self.lbl_counts.setStyleSheet("font-weight: bold; font-size: 12px; color: #5dade2;")
        layout.addWidget(self.lbl_counts)

        self.lbl_refinement = QLabel("Last refinement: –")
        self.lbl_refinement.setStyleSheet("font-size: 11px; color: #aaa;")
        self.lbl_refinement.setWordWrap(True)
        layout.addWidget(self.lbl_refinement)

        undo_row = QHBoxLayout()
        self.undo_button = QPushButton("↩ Undo")
        self.redo_button = QPushButton("↪ Redo")
        self.undo_button.clicked.connect(self.undo_requested.emit)
        self.redo_button.clicked.connect(self.redo_requested.emit)
        undo_row.addWidget(self.undo_button)
        undo_row.addWidget(self.redo_button)
        undo_row.addStretch(1)
        layout.addLayout(undo_row)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget { background-color: #232323; border: 1px solid #444; }
            QListWidget::item { border-bottom: 1px solid #333; }
            QListWidget::item:selected { background-color: #2d4d7d; }
        """)
        self.list_widget.currentItemChanged.connect(self._on_current_item_changed)
        layout.addWidget(self.list_widget, stretch=1)

        self.setWidget(container)

    def _on_current_item_changed(self, current, previous):
        if current is None:
            return
        prompt_id = current.data(Qt.ItemDataRole.UserRole)
        if prompt_id is not None:
            self.prompt_selected.emit(prompt_id)

    def refresh(self, prompts: list, refinement_verdict: dict = None):
        """Rebuild the list from the controller's current prompt list.
        Called on every on_prompt_list_changed -- simplest correct
        approach given how infrequently this changes (a handful of
        prompts per selection, not per-frame)."""
        selected_id = None
        current = self.list_widget.currentItem()
        if current is not None:
            selected_id = current.data(Qt.ItemDataRole.UserRole)

        self.list_widget.clear()
        for p in prompts:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, p.get('id'))
            row = PromptRowWidget(p)
            row.toggled.connect(self.prompt_toggled.emit)
            row.delete_clicked.connect(self.prompt_deleted.emit)
            item.setSizeHint(row.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, row)
            if p.get('id') == selected_id:
                self.list_widget.setCurrentItem(item)

        total = len(prompts)
        active = sum(1 for p in prompts if p.get('enabled', True))
        self.lbl_counts.setText(f"Prompts: {total} total, {active} active")

        if refinement_verdict and refinement_verdict.get('verdict'):
            v = refinement_verdict['verdict']
            label = {'improved': 'Improved', 'same': 'Stayed the same', 'regressed': 'Regressed'}[v]
            color = {'improved': '#4CAF50', 'same': '#5dade2', 'regressed': '#F44336'}[v]
            self.lbl_refinement.setText(
                f"Last refinement (prompt #{refinement_verdict.get('prompt_count', '?')}): "
                f"<span style='color:{color}; font-weight:bold;'>{label}</span> "
                f"({refinement_verdict.get('improved_count', 0)} metrics up, "
                f"{refinement_verdict.get('regressed_count', 0)} down)"
            )
        elif total > 0:
            self.lbl_refinement.setText("Last refinement: – (first prompt, nothing to compare yet)")
        else:
            self.lbl_refinement.setText("Last refinement: –")
