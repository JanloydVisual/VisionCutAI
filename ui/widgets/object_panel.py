from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QHBoxLayout, QLabel, QLineEdit, QCheckBox
)
from PyQt6.QtCore import pyqtSignal

class ObjectPanel(QWidget):
    """
    UI panel to manage multiple tracked objects with editing controls.
    """
    object_selected = pyqtSignal(str)
    object_created = pyqtSignal()
    object_removed = pyqtSignal(str)
    object_renamed = pyqtSignal(str, str) # obj_id, new_name
    object_visibility_changed = pyqtSignal(str, bool)
    object_lock_changed = pyqtSignal(str, bool)
    object_reordered = pyqtSignal(str, int) # obj_id, z_index

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Tracked Objects"))
        self.add_btn = QPushButton("+ New")
        self.add_btn.clicked.connect(self.object_created.emit)
        header_layout.addWidget(self.add_btn)
        self.layout.addLayout(header_layout)
        
        # List
        self.list_widget = QListWidget()
        self.list_widget.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.list_widget.currentItemChanged.connect(self._on_item_changed)
        self.list_widget.model().rowsMoved.connect(self._on_reorder)
        self.layout.addWidget(self.list_widget)
        
        # Edit Controls
        edit_layout = QHBoxLayout()
        self.rename_input = QLineEdit()
        self.rename_input.setPlaceholderText("Rename object...")
        self.rename_input.returnPressed.connect(self._on_rename)
        edit_layout.addWidget(self.rename_input)
        
        self.vis_cb = QCheckBox("Visible")
        self.vis_cb.setChecked(True)
        self.vis_cb.stateChanged.connect(self._on_visibility_toggled)
        edit_layout.addWidget(self.vis_cb)
        
        self.lock_cb = QCheckBox("Lock")
        self.lock_cb.stateChanged.connect(self._on_lock_toggled)
        edit_layout.addWidget(self.lock_cb)
        
        self.layout.addLayout(edit_layout)
        
        # Remove
        self.remove_btn = QPushButton("Remove Selected")
        self.remove_btn.clicked.connect(self._on_remove_clicked)
        self.layout.addWidget(self.remove_btn)
        
        self.object_map = {}
        
    def add_object(self, obj_id: str, name: str, status: str = "Idle", quality: str = "N/A"):
        item_text = f"{name} | Status: {status} | Quality: {quality}"
        item = QListWidgetItem(item_text)
        item.setData(100, obj_id)
        
        self.list_widget.addItem(item)
        self.object_map[obj_id] = item
        
        if self.list_widget.count() == 1:
            self.list_widget.setCurrentItem(item)
            
    def _on_rename(self):
        current = self.list_widget.currentItem()
        if current:
            new_name = self.rename_input.text().strip()
            if new_name:
                self.object_renamed.emit(current.data(100), new_name)
                
    def _on_visibility_toggled(self, state):
        current = self.list_widget.currentItem()
        if current:
            self.object_visibility_changed.emit(current.data(100), bool(state))
            
    def _on_lock_toggled(self, state):
        current = self.list_widget.currentItem()
        if current:
            self.object_lock_changed.emit(current.data(100), bool(state))
            
    def _on_reorder(self, parent, start, end, destination, row):
        # Emits new z_index order
        for idx in range(self.list_widget.count()):
            item = self.list_widget.item(idx)
            self.object_reordered.emit(item.data(100), idx)
            
    def _on_item_changed(self, current, previous):
        if current:
            obj_id = current.data(100)
            self.object_selected.emit(obj_id)
            
    def _on_remove_clicked(self):
        current = self.list_widget.currentItem()
        if current:
            obj_id = current.data(100)
            self.object_removed.emit(obj_id)
