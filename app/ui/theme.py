"""Premium design system tokens and global stylesheet for the Jarvis desktop app."""

from __future__ import annotations

FONT_UI = '"Segoe UI", "Nirmala UI", "Arial", sans-serif'
FONT_DISPLAY = '"Segoe UI", "Nirmala UI", "Arial", sans-serif'
FONT_MONO = '"Consolas", "Nirmala UI", "Segoe UI", monospace'
FONT_BANGLA = '"Nirmala UI", "Segoe UI", "Arial", sans-serif'
FONT_FAMILY = FONT_UI
DISPLAY_FAMILY = FONT_DISPLAY
UI_FAMILY = FONT_UI
# Legacy UI modules used MONO_FAMILY for general labels. Keep it readable while
# routing actual terminal/code surfaces through FONT_MONO or CODE_FAMILY.
MONO_FAMILY = FONT_UI
CODE_FAMILY = FONT_MONO

FONT_SIZE_TITLE = 24
FONT_SIZE_SUBTITLE = 13
FONT_SIZE_BODY = 13
FONT_SIZE_SMALL = 11
FONT_SIZE_CAPTION = 10
FONT_SIZE_DISPLAY = 26
FONT_SIZE_SECTION = 16
FONT_SIZE_BUTTON = 12
FONT_SIZE_INPUT = 14
FONT_WEIGHT_REGULAR = 500
FONT_WEIGHT_MEDIUM = 600
FONT_WEIGHT_SEMIBOLD = 700
FONT_WEIGHT_BOLD = 800
FONT_WEIGHT_HEAVY = 900

BG_ROOT = "#0a0d14"
BG_APP = "#0d1117"
BG_CANVAS = "#11161f"
BG_SIDEBAR = "#10141c"
BG_TOPBAR = "#141923"
SURFACE_1 = "#151a23"
SURFACE_2 = "#191f2a"
SURFACE_3 = "#202734"
SURFACE_ACTIVE = "#273246"
SURFACE_EDGE = "rgba(255,255,255,0.06)"
SURFACE_EDGE_BRIGHT = "rgba(255,255,255,0.10)"
INPUT_BG = "#10151d"
INPUT_FOCUS = "#121924"

ACCENT_PRIMARY = "#8fb4ff"
ACCENT_PRIMARY_STRONG = "#b1c9ff"
ACCENT_SECONDARY = "#a899ff"
ACCENT_SECONDARY_STRONG = "#c2b8ff"
ACCENT_SUPPORT = "#52d6b5"
ACCENT_MAGENTA = "#ec8ad0"
SUCCESS = "#47d7a1"
WARNING = "#ffbd66"
ERROR = "#f27f92"
TEXT_PRIMARY = "#f3f6fb"
TEXT_SECONDARY = "#d8dfeb"
TEXT_MUTED = "#93a0b4"
TEXT_FAINT = "#657186"

BORDER_SUBTLE = "rgba(255,255,255,0.05)"
BORDER_MID = "rgba(255,255,255,0.08)"
BORDER_PRIMARY = "rgba(143,180,255,0.22)"
BORDER_SECONDARY = "rgba(168,153,255,0.20)"
GLOW_PRIMARY = "rgba(143,180,255,0.12)"
GLOW_SECONDARY = "rgba(168,153,255,0.10)"
SHADOW_DARK = "rgba(0,0,0,0.24)"

SPACE_1 = 4
SPACE_2 = 8
SPACE_3 = 12
SPACE_4 = 16
SPACE_5 = 20
SPACE_6 = 24
SPACE_7 = 30
RADIUS_SM = 8
RADIUS_MD = 12
RADIUS_LG = 18
RADIUS_XL = 24

BG_NEURAL_DEEP = "#050810"
BG_NEURAL_CORE = "#0a0f1a"
BG_NEURAL_SURFACE = "#0f1628"
BG_NEURAL_PANEL = "#131a2e"
BG_NEURAL_CARD = "#171d32"
NEURAL_CYAN = "#00f5ff"
NEURAL_CYAN_DIM = "#00c4cc"
NEURAL_CYAN_GLOW = "rgba(0, 245, 255, 0.15)"
NEURAL_CYAN_BORDER = "rgba(0, 245, 255, 0.25)"
NEURAL_CYAN_BORDER_STRONG = "rgba(0, 245, 255, 0.45)"
NEURAL_BLUE = "#2f8cff"
NEURAL_BLUE_DIM = "#1d4ed8"
NEURAL_BLUE_GLOW = "rgba(47, 140, 255, 0.18)"
NEURAL_BLUE_BORDER = "rgba(47, 140, 255, 0.36)"
NEURAL_PURPLE = "#a855f7"
NEURAL_PURPLE_DIM = "#8b5cf6"
NEURAL_PURPLE_GLOW = "rgba(168, 85, 247, 0.12)"
NEURAL_PURPLE_BORDER = "rgba(168, 85, 247, 0.22)"
NEURAL_GREEN = "#19f5a6"
NEURAL_GREEN_GLOW = "rgba(25, 245, 166, 0.15)"
NEURAL_ORANGE = "#fb923c"
NEURAL_RED = "#f87171"
NEURAL_TEXT_PRIMARY = "#e2e8f0"
NEURAL_TEXT_SECONDARY = "#94a3b8"
NEURAL_TEXT_MUTED = "#64748b"
NEURAL_TEXT_MUTED_BLUE = "#6f86b9"
NEURAL_TEXT_CYAN = "#67e8f9"
NEURAL_GLOW_CYAN = "0 0 20px rgba(0, 245, 255, 0.3), 0 0 40px rgba(0, 245, 255, 0.1)"
NEURAL_GLOW_PURPLE = "0 0 20px rgba(168, 85, 247, 0.25), 0 0 40px rgba(168, 85, 247, 0.1)"
NEURAL_GLOW_GREEN = "0 0 15px rgba(34, 211, 238, 0.2)"
NEURAL_BORDER_CYAN = "1px solid rgba(0, 245, 255, 0.2)"
NEURAL_BORDER_PURPLE = "1px solid rgba(168, 85, 247, 0.2)"
NEURAL_BORDER_SUBTLE = "1px solid rgba(255, 255, 255, 0.04)"
NEURAL_BORDER_BLUE = "1px solid rgba(47, 140, 255, 0.28)"
NEURAL_BORDER_GLOW = "1px solid rgba(0, 245, 255, 0.34)"
ENABLE_NEURAL_ANIMATIONS = True

GLOBAL_STYLESHEET = f"""
QWidget {{
    font-family: {FONT_FAMILY};
    font-size: {FONT_SIZE_BODY}px;
    font-weight: {FONT_WEIGHT_REGULAR};
    color: {TEXT_PRIMARY};
    outline: none;
}}
QLabel {{
    font-family: {FONT_UI};
    font-size: {FONT_SIZE_BODY}px;
    font-weight: {FONT_WEIGHT_REGULAR};
}}
QMainWindow {{
    background: {BG_NEURAL_DEEP};
}}
QWidget#PageSurface, QWidget#PageContent, QScrollArea#PageScrollArea {{
    background: transparent;
    border: none;
}}
QDialog, QMessageBox {{
    background: {SURFACE_1};
    color: {TEXT_PRIMARY};
}}
QStackedWidget, QScrollArea, QScrollArea > QWidget > QWidget {{
    background: transparent;
    border: none;
}}
QMessageBox QLabel {{
    color: {TEXT_PRIMARY};
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px 0;
}}
QScrollBar::handle:vertical {{
    background: rgba(255,255,255,0.16);
    min-height: 40px;
    border-radius: 5px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
    height: 0;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 0 2px;
}}
QScrollBar::handle:horizontal {{
    background: rgba(255,255,255,0.16);
    min-width: 40px;
    border-radius: 5px;
}}
QLabel#PageTitle, QLabel#WorkspaceTitle, QLabel#NeuralPageTitle {{
    font-family: {FONT_DISPLAY};
    font-size: {FONT_SIZE_TITLE}px;
    font-weight: {FONT_WEIGHT_HEAVY};
    color: {NEURAL_TEXT_PRIMARY};
    letter-spacing: 0.4px;
}}
QLabel#PageSubtitle, QLabel#NeuralPageSubtitle, QLabel#SectionMeta, QLabel#MutedLabel {{
    font-family: {FONT_UI};
    color: {NEURAL_TEXT_SECONDARY};
    font-size: {FONT_SIZE_SUBTITLE}px;
    font-weight: {FONT_WEIGHT_MEDIUM};
}}
QLabel#PageEyebrow, QLabel#NeuralEyebrow {{
    font-family: {FONT_DISPLAY};
    font-size: {FONT_SIZE_CAPTION}px;
    color: {NEURAL_CYAN};
    font-weight: {FONT_WEIGHT_BOLD};
    letter-spacing: 1.4px;
    text-transform: uppercase;
}}
QLabel#CardTitle, QLabel#SectionTitle {{
    font-family: {FONT_DISPLAY};
    font-size: {FONT_SIZE_SECTION}px;
    font-weight: {FONT_WEIGHT_BOLD};
    color: {NEURAL_TEXT_PRIMARY};
}}
QFrame#PremiumCard, QFrame#AccentCard, QFrame#FeatureCard,
QFrame#NeuralPanel, QFrame#NeuralCard, QFrame#NeuralGlow,
QFrame#ConversationWorkspace, QFrame#ChatPanel, QFrame#ComposerPanel,
QFrame#UtilityPanel, QFrame#StatCard, QFrame#InfoPanel {{
    background: {BG_NEURAL_PANEL};
    border: {NEURAL_BORDER_SUBTLE};
    border-radius: 16px;
}}
QFrame#NeuralCard, QFrame#AccentCard {{
    border: {NEURAL_BORDER_CYAN};
}}
QFrame#NeuralCard[neural="purple"], QFrame#FeatureCard {{
    border: {NEURAL_BORDER_PURPLE};
}}
QPushButton {{
    font-family: {FONT_DISPLAY};
    font-size: {FONT_SIZE_BUTTON}px;
    font-weight: {FONT_WEIGHT_SEMIBOLD};
}}
QPushButton#PrimaryButton, QPushButton#NeuralPrimaryButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00d4ff, stop:1 {NEURAL_CYAN});
    color: #08111f;
    border: none;
    border-radius: 12px;
    padding: 10px 18px;
    font-weight: 900;
}}
QPushButton#PrimaryButton:hover, QPushButton#NeuralPrimaryButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #22d3ee, stop:1 #67e8f9);
}}
QPushButton#SecondaryButton, QPushButton#GhostButton, QPushButton#UtilityButton,
QPushButton#NeuralSecondaryButton, QPushButton#NeuralGhostButton, QPushButton#NeuralChip {{
    background: rgba(0, 245, 255, 0.06);
    color: {NEURAL_TEXT_PRIMARY};
    border: 1px solid rgba(0, 245, 255, 0.16);
    border-radius: 10px;
    padding: 9px 14px;
}}
QPushButton#SecondaryButton:hover, QPushButton#GhostButton:hover, QPushButton#UtilityButton:hover,
QPushButton#NeuralSecondaryButton:hover, QPushButton#NeuralGhostButton:hover, QPushButton#NeuralChip:hover {{
    background: rgba(0, 245, 255, 0.12);
    border-color: rgba(0, 245, 255, 0.3);
    color: {NEURAL_CYAN};
}}
QPushButton#DangerButton {{
    background: rgba(248, 113, 113, 0.14);
    color: #ffe6eb;
    border: 1px solid rgba(248, 113, 113, 0.28);
    border-radius: 10px;
    padding: 9px 14px;
}}
QLineEdit, QSpinBox, QTextEdit, QPlainTextEdit, QListWidget, QComboBox {{
    font-family: {FONT_UI};
    font-size: {FONT_SIZE_INPUT}px;
    font-weight: {FONT_WEIGHT_MEDIUM};
    background: {INPUT_BG};
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px;
    color: {TEXT_PRIMARY};
    selection-background-color: rgba(0, 245, 255, 0.24);
    selection-color: #ffffff;
}}
QLineEdit, QSpinBox, QComboBox {{
    padding: 8px 12px;
    min-height: 20px;
}}
QTextEdit#ChatLog, QTextEdit#PlainLog, QTextEdit#VisionOutput, QTextEdit#CommandInput, QTextEdit#NeuralInput {{
    background: {BG_NEURAL_CORE};
    border: 1px solid rgba(0, 245, 255, 0.12);
    border-radius: 14px;
    padding: 12px;
}}
QTextEdit#PlainLog, QTextEdit#VisionOutput {{
    font-family: {CODE_FAMILY};
    font-size: {FONT_SIZE_SMALL}px;
}}
QLineEdit:focus, QSpinBox:focus, QTextEdit:focus, QListWidget:focus, QComboBox:focus {{
    border: 1px solid rgba(0, 245, 255, 0.35);
    background: {INPUT_FOCUS};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background: {SURFACE_1};
    border: 1px solid rgba(255,255,255,0.10);
    selection-background-color: rgba(0,245,255,0.16);
    color: {TEXT_PRIMARY};
}}
QCheckBox {{
    spacing: 8px;
    color: {TEXT_SECONDARY};
    font-weight: 600;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 5px;
    border: 1px solid rgba(255,255,255,0.18);
    background: {INPUT_BG};
}}
QCheckBox::indicator:checked {{
    background: {NEURAL_CYAN};
    border-color: {NEURAL_CYAN};
}}
QListWidget {{
    padding: 6px;
}}
QListWidget::item {{
    padding: 9px 10px;
    border-radius: 9px;
    color: {TEXT_SECONDARY};
}}
QListWidget::item:hover {{
    background: rgba(0,245,255,0.06);
}}
QListWidget::item:selected {{
    background: rgba(0,245,255,0.14);
    color: {TEXT_PRIMARY};
}}
QToolTip {{
    background: {SURFACE_1};
    color: {TEXT_PRIMARY};
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 8px;
    padding: 6px 8px;
}}
"""
