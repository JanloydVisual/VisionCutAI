def get_stylesheet():
    return """
    /* Global Default styling */
    * {
        font-family: "Segoe UI", sans-serif;
        font-size: 13px;
        color: #E6E6E6;
        background-color: #181818;
    }

    /* Main Window Background */
    QMainWindow {
        background-color: #181818;
    }

    /* QWidget backgrounds that shouldn't be overridden */
    QWidget {
        background-color: transparent;
    }
    
    QDialog, QMessageBox {
        background-color: #222222;
    }

    /* Dock Widgets */
    QDockWidget {
        titlebar-close-icon: url(close.png);
        titlebar-normal-icon: url(float.png);
        border: 1px solid #3A3A3A;
        background-color: #222222;
        color: #E6E6E6;
    }
    QDockWidget::title {
        background: #181818;
        padding-left: 5px;
        padding-top: 2px;
        border-bottom: 1px solid #3A3A3A;
        font-weight: bold;
    }

    /* Splitter Handles */
    QSplitter::handle {
        background-color: #3A3A3A;
        margin: 1px;
    }
    QSplitter::handle:hover {
        background-color: #35D07F;
    }
    QSplitter::handle:pressed {
        background-color: #2A9F63;
    }

    /* Buttons */
    QPushButton {
        background-color: #222222;
        border: 1px solid #3A3A3A;
        border-radius: 4px;
        padding: 4px 12px;
        color: #E6E6E6;
    }
    QPushButton:hover {
        background-color: #2A2A2A;
        border: 1px solid #35D07F;
    }
    QPushButton:pressed {
        background-color: #35D07F;
        color: #181818;
    }
    QPushButton:checked {
        background-color: #3A3A3A;
        border: 1px solid #35D07F;
        color: #35D07F;
    }

    /* Inputs and Dropdowns */
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
        background-color: #181818;
        border: 1px solid #3A3A3A;
        border-radius: 3px;
        padding: 4px;
        color: #E6E6E6;
    }
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
        border: 1px solid #35D07F;
    }
    
    QComboBox::drop-down {
        border: none;
    }
    QComboBox QAbstractItemView {
        background-color: #222222;
        border: 1px solid #3A3A3A;
        selection-background-color: #35D07F;
        selection-color: #181818;
    }

    /* Status Bar */
    QStatusBar {
        background-color: #222222;
        border-top: 1px solid #3A3A3A;
        color: #E6E6E6;
        font-size: 11px;
    }
    QStatusBar::item {
        border: none;
    }

    /* Toolbars */
    QToolBar {
        background-color: #222222;
        border-bottom: 1px solid #3A3A3A;
        spacing: 10px;
        padding: 2px;
    }
    QToolBar::separator {
        width: 1px;
        background-color: #3A3A3A;
        margin: 4px 8px;
    }

    /* Viewer / Player (using object name to target specifically if needed, but VideoPlayerWidget should handle it internally or transparently) */
    #ViewerWidget {
        background-color: #000000;
        border: none;
    }

    /* Scrollbars */
    QScrollBar:vertical {
        border: none;
        background: #181818;
        width: 12px;
        margin: 0px 0px 0px 0px;
    }
    QScrollBar::handle:vertical {
        background: #3A3A3A;
        min-height: 20px;
        border-radius: 6px;
    }
    QScrollBar::handle:vertical:hover {
        background: #4A4A4A;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        border: none;
        background: none;
    }
    
    QScrollBar:horizontal {
        border: none;
        background: #181818;
        height: 12px;
        margin: 0px 0px 0px 0px;
    }
    QScrollBar::handle:horizontal {
        background: #3A3A3A;
        min-width: 20px;
        border-radius: 6px;
    }
    QScrollBar::handle:horizontal:hover {
        background: #4A4A4A;
    }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        border: none;
        background: none;
    }

    /* Menus */
    QMenuBar {
        background-color: #222222;
        color: #E6E6E6;
        border-bottom: 1px solid #3A3A3A;
    }
    QMenuBar::item:selected {
        background-color: #3A3A3A;
    }
    QMenu {
        background-color: #222222;
        color: #E6E6E6;
        border: 1px solid #3A3A3A;
    }
    QMenu::item:selected {
        background-color: #35D07F;
        color: #181818;
    }
    
    /* Progress Bar */
    QProgressBar {
        border: 1px solid #3A3A3A;
        border-radius: 4px;
        text-align: center;
        background-color: #181818;
    }
    QProgressBar::chunk {
        background-color: #35D07F;
        border-radius: 3px;
    }
    """
