"""UI theme definitions for FL Lingo."""

from __future__ import annotations


THEMES = {
    "light": """
        QWidget { background: #f5f4ef; color: #1f1a17; }
        QMainWindow, QDialog { background: #f5f4ef; }
        QLineEdit, QTextEdit, QComboBox, QTableWidget {
            background: #fffdf8;
            color: #1f1a17;
            border: 1px solid #c9c0b3;
            selection-background-color: #d97841;
            selection-color: #ffffff;
        }
        QLineEdit:hover, QTextEdit:hover, QComboBox:hover, QTableWidget:hover {
            border: 1px solid #d97841;
        }
        QPushButton {
            background: #1f5c5c;
            color: #ffffff;
            border: 1px solid #1f5c5c;
            border-radius: 6px;
            padding: 6px 10px;
        }
        QPushButton:hover {
            background: #267171;
            border-color: #d97841;
        }
        QPushButton:pressed {
            background: #184a4a;
            border-color: #b85e2c;
            padding-top: 7px;
            padding-bottom: 5px;
        }
        QPushButton:disabled {
            background: #97a4a4;
            color: #e7ecec;
            border-color: #97a4a4;
        }
        QTabWidget::pane, QGroupBox {
            border: 1px solid #c9c0b3;
            margin-top: 10px;
        }
        QMenuBar {
            background: #ece4d7;
            color: #1f1a17;
            border-bottom: 1px solid #c9c0b3;
        }
        QMenuBar::item {
            background: transparent;
            padding: 6px 10px;
            margin: 1px 2px;
            border-radius: 4px;
        }
        QMenuBar::item:selected {
            background: #f7efe3;
            color: #103c52;
        }
        QMenuBar::item:pressed {
            background: #d97841;
            color: #ffffff;
        }
        QMenu {
            background: #fffdf8;
            color: #1f1a17;
            border: 1px solid #c9c0b3;
        }
        QMenu::item {
            padding: 6px 24px 6px 12px;
        }
        QMenu::item:selected {
            background: #d97841;
            color: #ffffff;
        }
        QTabBar::tab {
            background: #e8e0d4;
            color: #1f1a17;
            border: 1px solid #c9c0b3;
            border-bottom: none;
            padding: 7px 12px;
            margin-right: 2px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
        }
        QTabBar::tab:hover {
            background: #f3ebdf;
            color: #103c52;
        }
        QTabBar::tab:selected {
            background: #fffdf8;
            color: #103c52;
            border-color: #d97841;
        }
        QComboBox::drop-down {
            border: none;
            width: 22px;
        }
        QCheckBox:hover, QGroupBox:hover {
            color: #103c52;
        }
        QTableWidget::item:selected {
            background: #d97841;
            color: #ffffff;
        }
        QHeaderView::section:hover {
            background: #efe6d9;
            color: #103c52;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 4px;
        }
    """,
    "dark": """
        QWidget { background: #1f2329; color: #e6edf3; }
        QLineEdit, QTextEdit, QComboBox, QTableWidget {
            background: #2d333b;
            color: #e6edf3;
            border: 1px solid #444c56;
        }
        QLineEdit:hover, QTextEdit:hover, QComboBox:hover, QTableWidget:hover {
            border: 1px solid #58a6ff;
        }
        QPushButton {
            background: #2f81f7;
            color: white;
            border: 1px solid #2f81f7;
            border-radius: 6px;
            padding: 6px 10px;
        }
        QPushButton:hover {
            background: #4493f8;
            border-color: #79c0ff;
        }
        QPushButton:pressed {
            background: #1f6feb;
            border-color: #1f6feb;
            padding-top: 7px;
            padding-bottom: 5px;
        }
        QPushButton:disabled {
            background: #4b5563;
            color: #c9d1d9;
            border-color: #4b5563;
        }
        QTabBar::tab {
            background: #2d333b;
            color: #c9d1d9;
            border: 1px solid #444c56;
            border-bottom: none;
            padding: 7px 12px;
            margin-right: 2px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
        }
        QTabBar::tab:hover {
            background: #343b43;
            color: #ffffff;
        }
        QTabBar::tab:selected {
            background: #1f2329;
            color: #79c0ff;
            border-color: #58a6ff;
        }
        QComboBox::drop-down {
            border: none;
            width: 22px;
        }
        QCheckBox:hover, QGroupBox:hover {
            color: #79c0ff;
        }
        QTableWidget::item:selected {
            background: #2f81f7;
            color: #ffffff;
        }
        QHeaderView::section:hover {
            background: #343b43;
            color: #ffffff;
        }
        QGroupBox {
            border: 1px solid #444c56;
            margin-top: 10px;
        }
        QMenuBar {
            background: #161b22;
            color: #e6edf3;
            border-bottom: 1px solid #30363d;
        }
        QMenuBar::item {
            background: transparent;
            padding: 6px 10px;
            margin: 1px 2px;
            border-radius: 4px;
        }
        QMenuBar::item:selected {
            background: #30363d;
            color: #ffffff;
        }
        QMenuBar::item:pressed {
            background: #2f81f7;
            color: #ffffff;
        }
        QMenu {
            background: #1f2329;
            color: #e6edf3;
            border: 1px solid #444c56;
        }
        QMenu::item {
            padding: 6px 24px 6px 12px;
        }
        QMenu::item:selected {
            background: #2f81f7;
            color: #ffffff;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 4px;
        }
    """,
    "high_contrast": """
        QWidget { background: #000000; color: #ffffff; }
        QMainWindow, QDialog { background: #000000; }
        QLineEdit, QTextEdit, QComboBox, QTableWidget {
            background: #000000;
            color: #ffffff;
            border: 2px solid #ffff00;
            selection-background-color: #00ffff;
            selection-color: #000000;
        }
        QLineEdit:hover, QTextEdit:hover, QComboBox:hover, QTableWidget:hover {
            border: 2px solid #00ffff;
        }
        QPushButton {
            background: #ffff00;
            color: #000000;
            border: 2px solid #ffffff;
            padding: 6px 10px;
            font-weight: bold;
            border-radius: 6px;
        }
        QPushButton:hover {
            background: #00ffff;
            color: #000000;
            border-color: #ffff00;
        }
        QPushButton:pressed {
            background: #ff8c00;
            color: #000000;
            border-color: #ffffff;
            padding-top: 7px;
            padding-bottom: 5px;
        }
        QPushButton:disabled {
            background: #666666;
            color: #ffffff;
            border: 2px solid #999999;
        }
        QLabel, QCheckBox, QGroupBox, QTabBar::tab {
            color: #ffffff;
        }
        QMenuBar {
            background: #000000;
            color: #ffffff;
            border-bottom: 2px solid #ffffff;
        }
        QMenuBar::item {
            background: transparent;
            padding: 6px 10px;
            margin: 1px 2px;
        }
        QMenuBar::item:selected {
            background: #00ffff;
            color: #000000;
        }
        QMenuBar::item:pressed {
            background: #ffff00;
            color: #000000;
        }
        QMenu {
            background: #000000;
            color: #ffffff;
            border: 2px solid #ffffff;
        }
        QMenu::item {
            padding: 6px 24px 6px 12px;
        }
        QMenu::item:selected {
            background: #00ffff;
            color: #000000;
        }
        QTabBar::tab {
            background: #000000;
            border: 2px solid #ffffff;
            border-bottom: none;
            padding: 7px 12px;
            margin-right: 2px;
        }
        QTabBar::tab:hover {
            background: #00ffff;
            color: #000000;
            border-color: #ffff00;
        }
        QTabBar::tab:selected {
            background: #ffff00;
            color: #000000;
            border-color: #ffffff;
        }
        QComboBox::drop-down {
            border: none;
            width: 22px;
        }
        QCheckBox:hover, QGroupBox:hover {
            color: #00ffff;
        }
        QTableWidget::item:selected {
            background: #00ffff;
            color: #000000;
        }
        QTabWidget::pane, QGroupBox {
            border: 2px solid #ffffff;
            margin-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 4px;
        }
        QHeaderView::section {
            background: #000000;
            color: #ffffff;
            border: 1px solid #ffff00;
        }
        QHeaderView::section:hover {
            background: #00ffff;
            color: #000000;
        }
    """,
}
