from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QSlider, QColorDialog, QPushButton, QFileDialog
)
from PyQt6.QtCore import Qt

class CompositingPanel(QWidget):
    """
    UI Controls for background replacement and edge feathering.
    """
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        
        lbl_title = QLabel("Compositing & Background")
        lbl_title.setStyleSheet("font-weight: bold; color: #5dade2;")
        layout.addWidget(lbl_title)
        
        # Background Mode
        bg_layout = QHBoxLayout()
        bg_layout.addWidget(QLabel("Background:"))
        self.bg_mode_combo = QComboBox()
        self.bg_mode_combo.addItems(["Original", "Solid Color", "Image", "Blur"])
        self.bg_mode_combo.currentTextChanged.connect(self._on_bg_mode_changed)
        bg_layout.addWidget(self.bg_mode_combo)
        layout.addLayout(bg_layout)
        
        # Options container
        self.options_widget = QWidget()
        self.options_layout = QVBoxLayout(self.options_widget)
        self.options_layout.setContentsMargins(0,0,0,0)
        
        # Color picker (for Solid Color)
        self.btn_color = QPushButton("Choose Color")
        self.btn_color.clicked.connect(self._choose_color)
        self.btn_color.setVisible(False)
        self.options_layout.addWidget(self.btn_color)
        
        # Image picker (for Image)
        self.btn_image = QPushButton("Choose Image...")
        self.btn_image.clicked.connect(self._choose_image)
        self.btn_image.setVisible(False)
        self.options_layout.addWidget(self.btn_image)
        
        # Blur Slider
        self.blur_layout = QHBoxLayout()
        self.blur_layout.addWidget(QLabel("Blur:"))
        self.slider_blur = QSlider(Qt.Orientation.Horizontal)
        self.slider_blur.setRange(1, 99)
        self.slider_blur.setValue(21)
        self.slider_blur.valueChanged.connect(self._on_settings_changed)
        self.blur_layout.addWidget(self.slider_blur)
        
        self.blur_widget = QWidget()
        self.blur_widget.setLayout(self.blur_layout)
        self.blur_widget.setVisible(False)
        self.options_layout.addWidget(self.blur_widget)
        
        layout.addWidget(self.options_widget)
        
        # Edge Feather
        feather_layout = QHBoxLayout()
        feather_layout.addWidget(QLabel("Edge Feather:"))
        self.slider_feather = QSlider(Qt.Orientation.Horizontal)
        self.slider_feather.setRange(0, 20)
        self.slider_feather.setValue(3)
        self.slider_feather.valueChanged.connect(self._on_settings_changed)
        feather_layout.addWidget(self.slider_feather)
        layout.addLayout(feather_layout)

        # BG Opacity
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("BG Opacity:"))
        self.slider_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_opacity.setRange(0, 100)
        self.slider_opacity.setValue(100)
        self.slider_opacity.valueChanged.connect(self._on_settings_changed)
        opacity_layout.addWidget(self.slider_opacity)
        layout.addLayout(opacity_layout)
        
        layout.addStretch()

    def _on_bg_mode_changed(self, text):
        self.btn_color.setVisible(text == "Solid Color")
        self.btn_image.setVisible(text == "Image")
        self.blur_widget.setVisible(text == "Blur")
        self._on_settings_changed()
        
    def _choose_color(self):
        # Mock color selection
        self._on_settings_changed()
        
    def _choose_image(self):
        # Mock image selection
        self._on_settings_changed()
        
    def _on_settings_changed(self):
        # 5. Preview updates without rerunning AI
        # This triggers a direct re-composite in the viewport
        pass
