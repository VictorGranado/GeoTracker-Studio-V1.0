APP_QSS = r'''
QMainWindow, QWidget {
    background: #0d1117;
    color: #e6edf3;
    font-family: "Segoe UI";
    font-size: 10pt;
}
QFrame#Sidebar {
    background: #111821;
    border-right: 1px solid #263241;
}
QFrame#BrandPanel {
    background: transparent;
    border-bottom: 1px solid #263241;
}
QLabel#BrandMark { background: transparent; }
QLabel#Brand {
    font-size: 17pt;
    font-weight: 750;
    color: #f0f6fc;
}
QLabel#BrandSub {
    color: #9aa8b6;
    font-size: 8pt;
    font-weight: 650;
    letter-spacing: 1px;
}
QLabel#VersionBadge {
    color: #9ecbff;
    background: #16263a;
    border: 1px solid #294c73;
    border-radius: 6px;
    padding: 1px 6px;
    font-size: 7.5pt;
    font-weight: 650;
}
QLabel#SidebarSection {
    color: #667788;
    font-size: 7.5pt;
    font-weight: 700;
    letter-spacing: 1px;
    padding: 2px 4px 4px 4px;
}
QPushButton#NavButton {
    text-align: left;
    padding: 10px 13px;
    border: none;
    border-radius: 7px;
    background: transparent;
    color: #b8c4cf;
    font-weight: 500;
}
QPushButton#NavButton:hover {
    background: #17212c;
    color: #ffffff;
}
QPushButton#NavButton:checked {
    background: #1b2a3a;
    color: #ffffff;
    border-left: 3px solid #58a6ff;
}
QPushButton#PrimaryButton {
    padding: 10px 13px;
    border: 1px solid #388bfd;
    border-radius: 7px;
    background: #1f6feb;
    color: white;
    font-weight: 600;
}
QPushButton#PrimaryButton:hover { background: #388bfd; }
QLabel#PageTitle {
    font-size: 22pt;
    font-weight: 700;
    color: #f0f6fc;
}
QLabel#PageSubtitle { color: #8b949e; font-size: 10pt; }
QFrame#Card {
    background: #151c24;
    border: 1px solid #273444;
    border-radius: 10px;
}
QLabel#CardLabel { color: #8b949e; font-size: 9pt; }
QLabel#CardValue { color: #f0f6fc; font-size: 18pt; font-weight: 700; }
QLabel#CardDetail { color: #768390; font-size: 8.5pt; }
QFrame#Panel {
    background: #151c24;
    border: 1px solid #273444;
    border-radius: 10px;
}
QLabel#PanelTitle { font-size: 12pt; font-weight: 650; color: #f0f6fc; }
QTableWidget {
    background: #111821;
    alternate-background-color: #141d27;
    border: 1px solid #273444;
    border-radius: 8px;
    gridline-color: #273444;
    selection-background-color: #1f6feb;
    selection-color: white;
}
QHeaderView::section {
    background: #1a2430;
    color: #aebbc8;
    border: none;
    border-right: 1px solid #273444;
    border-bottom: 1px solid #273444;
    padding: 7px;
    font-weight: 600;
}
QScrollBar:vertical { background: #111821; width: 10px; }
QScrollBar::handle:vertical { background: #344454; border-radius: 5px; min-height: 24px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QStatusBar { background: #0b0f14; color: #8b949e; border-top: 1px solid #263241; }
QLabel#GoodStatus { color: #3fb950; font-weight: 600; }
QLabel#WarningStatus { color: #d29922; font-weight: 600; }
QLabel#Muted { color: #8b949e; }
QLabel#PlaceholderIcon { color: #58a6ff; font-size: 30pt; font-weight: 700; }
'''

# Phase 2B additions
APP_QSS += r'''
QPushButton#SecondaryButton {
    background: #151c24;
    color: #c9d1d9;
    border: 1px solid #344454;
    border-radius: 7px;
    padding: 7px 13px;
    font-weight: 600;
}
QPushButton#SecondaryButton:hover { background: #1a2430; border-color: #58a6ff; }
QComboBox {
    background: #111821;
    color: #c9d1d9;
    border: 1px solid #344454;
    border-radius: 6px;
    padding: 6px 28px 6px 9px;
    min-width: 150px;
}
QComboBox:hover { border-color: #58a6ff; }
QComboBox#MapCombo { min-width: 135px; max-width: 175px; }
QComboBox#OverlayCombo { min-width: 145px; max-width: 190px; }
QComboBox#ScaleCombo { min-width: 64px; max-width: 82px; }
QComboBox QAbstractItemView {
    background: #151c24;
    color: #c9d1d9;
    selection-background-color: #1f6feb;
    border: 1px solid #344454;
}
QSplitter::handle { background: #263241; width: 1px; }
'''

# Phase 2E additions
APP_QSS += r'''
QCheckBox {
    color: #c9d1d9;
    spacing: 8px;
    padding: 3px;
}
QPushButton:disabled {
    background: #151c24;
    color: #58636f;
    border-color: #273444;
}
'''


# Phase 2H release polish
APP_QSS += r'''
QMenuBar {
    background: #0b0f14;
    color: #aebbc8;
    border-bottom: 1px solid #1d2833;
    padding: 2px;
}
QMenuBar::item { padding: 5px 9px; border-radius: 4px; }
QMenuBar::item:selected { background: #17212c; color: #ffffff; }
QMenu {
    background: #111821;
    color: #c9d1d9;
    border: 1px solid #344454;
    padding: 5px;
}
QMenu::item { padding: 7px 28px 7px 10px; border-radius: 4px; }
QMenu::item:selected { background: #1f6feb; color: white; }
QPushButton#NavButton { padding-left: 11px; }
QFrame#DemoBanner {
    background: #171d22;
    border: 1px solid #594a20;
    border-radius: 8px;
}
QLabel#DemoBadge {
    color: #f2cc60;
    background: #302a19;
    border: 1px solid #66551d;
    border-radius: 5px;
    padding: 2px 7px;
    font-size: 7.5pt;
    font-weight: 700;
    letter-spacing: 0.6px;
}
QLabel#DemoBannerText { color: #c9d1d9; }
QLabel#AboutTitle { font-size: 20pt; font-weight: 700; }
QLabel#AboutBody { color: #c9d1d9; }
QFrame#Divider { color: #263241; background: #263241; max-height: 1px; }
QDialog { background: #0d1117; color: #e6edf3; }
QDialogButtonBox QPushButton {
    background: #151c24; color: #c9d1d9; border: 1px solid #344454;
    border-radius: 7px; padding: 7px 16px; min-width: 72px;
}
QDialogButtonBox QPushButton:hover { border-color: #58a6ff; background: #1a2430; }
'''
