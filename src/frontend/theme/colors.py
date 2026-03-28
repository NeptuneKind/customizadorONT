_STYLE_TEMPLATE = """
QMainWindow {{
    background: {window_bg};
}}

QWidget {{
    color: {text_primary};
    font-size: 13px;
}}

QWidget#sidebar {{
    background: {sidebar_bg};
    border-right: 1px solid {border_color};
}}

QLabel#sidebarTitle {{
    font-size: 22px;
    font-weight: 700;
    color: {text_primary};
}}

QLabel#sidebarSubtitle {{
    font-size: 12px;
    color: {text_muted};
}}

QFrame[card="true"], QWidget[card="true"] {{
    background: {card_bg};
    border: 1px solid {border_color};
    border-radius: 18px;
}}

QLabel[cardTitle="true"] {{
    font-size: 18px;
    font-weight: 700;
    color: {text_primary};
}}

QLabel[cardSubtitle="true"] {{
    font-size: 12px;
    color: {text_muted};
}}

QPushButton {{
    background: {button_bg};
    color: {text_primary};
    border: 1px solid {border_color};
    border-radius: 10px;
    min-height: 40px;
    padding: 8px 12px;
}}

QPushButton:hover {{
    background: {button_hover};
}}

QPushButton[active="true"] {{
    background: {accent};
    border: 1px solid {accent};
    color: #FFFFFF;
}}

QPushButton[slotSelected="true"] {{
    background: {accent};
    border: 2px solid #FFFFFF;
    color: #FFFFFF;
}}

QPushButton[slotSelected="false"] {{
    background: {button_bg};
    border: 1px solid {border_color};
    color: {text_primary};
}}

QLineEdit, QComboBox, QTextEdit, QPlainTextEdit {{
    background: {input_bg};
    color: {text_primary};
    border: 1px solid {accent_soft};
    border-radius: 10px;
    min-height: 38px;
    padding: 6px 10px;
}}

QLineEdit:disabled, QComboBox:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
    background: {input_disabled_bg};
    color: {input_disabled_text};
    border: 1px solid {border_color};
}}

QLabel[muted="true"] {{
    color: {text_muted};
}}

QLabel[badge="pending"] {{
    background: #64748B;
    color: #FFFFFF;
    border-radius: 12px;
    padding: 8px 16px;
    font-size: 14px;
    font-weight: 700;
}}

QLabel[badge="running"] {{
    background: #38BDF8;
    color: #FFFFFF;
    border-radius: 12px;
    padding: 8px 16px;
    font-size: 14px;
    font-weight: 700;
}}

QLabel[badge="success"] {{
    background: #22C55E;
    color: #FFFFFF;
    border-radius: 12px;
    padding: 8px 16px;
    font-size: 14px;
    font-weight: 700;  
}}

QLabel[badge="error"] {{
    background: #EF4444;
    color: #FFFFFF;
    border-radius: 12px;
    padding: 8px 16px;
    font-size: 14px;
    font-weight: 700;
}}

QCheckBox {{
    spacing: 10px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 9px;
    border: 1px solid {checkbox_border};
    background: {checkbox_bg};
}}

QCheckBox::indicator:checked {{
    background: {accent};
    border: 1px solid {accent};
}}
"""

LIGHT_THEME = _STYLE_TEMPLATE.format(
    window_bg="#F8FAFC",
    text_primary="#0F172A",
    sidebar_bg="#E2E8F0",
    border_color="#CBD5E1",
    card_bg="#FFFFFF",
    text_muted="#64748B",
    button_bg="#E2E8F0",
    button_hover="#CBD5E1",
    accent="#2563EB",
    accent_soft="#60A5FA",
    input_bg="#FFFFFF",
    input_disabled_bg="#F1F5F9",
    input_disabled_text="#94A3B8",
    checkbox_border="#94A3B8",
    checkbox_bg="#FFFFFF",
)

DARK_THEME = _STYLE_TEMPLATE.format(
    window_bg="#0F172A",
    text_primary="#E5E7EB",
    sidebar_bg="#111827",
    border_color="#334155",
    card_bg="#1F2937",
    text_muted="#94A3B8",
    button_bg="#243041",
    button_hover="#334155",
    accent="#2563EB",
    accent_soft="#3B82F6",
    input_bg="#0B1220",
    input_disabled_bg="#1E293B",
    input_disabled_text="#6B7280",
    checkbox_border="#334155",
    checkbox_bg="#243041",
)

APP_STYLE = DARK_THEME

def get_app_style(theme_mode: str) -> str:
    return DARK_THEME if theme_mode == "dark" else LIGHT_THEME