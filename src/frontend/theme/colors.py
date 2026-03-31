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
    border-radius: 20px;
}}

QLabel[cardTitle="true"] {{
    font-size: 18px;
    font-weight: 700;
    color: {text_primary};
}}

QLabel[cardSubtitle="true"] {{
    font-size: 12px;
    color: {help_text};
}}

QPushButton {{
    background: {button_bg};
    color: {text_primary};
    border: 1px solid {button_border};
    border-radius: 10px;
    min-height: 40px;
    padding: 8px 12px;
}}

QPushButton:hover {{
    background: {button_hover};
    border: 1px solid {button_hover_border};
}}

QPushButton[active="true"] {{
    background: {accent};
    border: 1px solid {accent};
    color: #FFFFFF;
    font-weight: 700;
}}

QPushButton[slotSelected="true"] {{
    background: {slot_selected_bg};
    color: {slot_selected_text};
    border: 2px solid {slot_selected_border};
    font-weight: 700;
}}

QPushButton[slotSelected="true"]:hover {{
    background: {slot_selected_bg_hover};
    color: {slot_selected_text};
    border: 2px solid {slot_selected_border};
}}

QPushButton[slotSelected="false"] {{
    background: {slot_unselected_bg};
    color: {text_primary};
    border: 1px solid {slot_unselected_border};
}}

QPushButton[slotSelected="false"]:hover {{
    background: {slot_unselected_hover};
    color: {text_primary};
    border: 1px solid {slot_unselected_border};
}}

QLineEdit, QComboBox, QTextEdit, QPlainTextEdit {{
    background: {input_bg};
    color: {text_primary};
    border: 1px solid {input_border};
    border-radius: 10px;
    min-height: 38px;
    padding: 6px 10px;
}}

QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {input_focus_border};
}}

QLineEdit:disabled, QComboBox:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
    background: {input_disabled_bg};
    color: {input_disabled_text};
    border: 1px solid {border_color};
}}

QLabel[muted="true"] {{
    color: {help_text};
}}

QLabel[badge="pending"] {{
    background: {badge_pending_bg};
    color: #FFFFFF;
    border-radius: 12px;
    padding: 8px 16px;
    font-size: 14px;
    font-weight: 700;
}}

QLabel[badge="running"] {{
    background: {badge_running_bg};
    color: #FFFFFF;
    border-radius: 12px;
    padding: 8px 16px;
    font-size: 14px;
    font-weight: 700;
}}

QLabel[badge="success"] {{
    background: {badge_success_bg};
    color: #FFFFFF;
    border-radius: 12px;
    padding: 8px 16px;
    font-size: 14px;
    font-weight: 700;
}}

QLabel[badge="error"] {{
    background: {badge_error_bg};
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

QScrollArea#leftPlansScroll QScrollBar:vertical {{
    background: transparent;
    width: 12px;
    margin: 6px 2px 6px 2px;
    border: none;
}}

QScrollArea#leftPlansScroll QScrollBar::handle:vertical {{
    background: {scroll_handle};
    min-height: 36px;
    border-radius: 6px;
    border: 1px solid {scroll_handle_border};
}}

QScrollArea#leftPlansScroll QScrollBar::handle:vertical:hover {{
    background: {scroll_handle_hover};
}}

QScrollArea#leftPlansScroll QScrollBar::add-line:vertical,
QScrollArea#leftPlansScroll QScrollBar::sub-line:vertical {{
    height: 0px;
    border: none;
    background: transparent;
}}

QScrollArea#leftPlansScroll QScrollBar::add-page:vertical,
QScrollArea#leftPlansScroll QScrollBar::sub-page:vertical {{
    background: transparent;
}}

QScrollArea#leftPlansScroll QScrollBar:horizontal {{
    height: 0px;
    background: transparent;
}}

QScrollArea#settingsScroll {{
    border: none;
    background: transparent;
}}

QWidget#settingsScrollViewport {{
    background: transparent;
}}
"""

LIGHT_THEME = _STYLE_TEMPLATE.format(
    window_bg="#FFFFFF",
    text_primary="#333333",
    text_muted="#6C757D",
    help_text="#317ACF",
    sidebar_bg="#F5F9FA",
    border_color="#DCE6EA",
    card_bg="#FFFFFF",
    button_bg="#FFFFFF",
    button_border="#CFE0E5",
    button_hover="#F1FBFC",
    button_hover_border="#3DC1CC",
    accent="#00968F",
    input_bg="#FFFFFF",
    input_border="#DCE6EA",
    input_focus_border="#CADFF7",
    input_disabled_bg="#F4F7F8",
    input_disabled_text="#98A6AE",
    checkbox_border="#A8BCC3",
    checkbox_bg="#FFFFFF",
    scroll_handle="#CFDDE1",
    scroll_handle_border="#B7C8CE",
    scroll_handle_hover="#3DC1CC",
    slot_selected_bg="#3DC1CC",
    slot_selected_text="#11353A",
    slot_selected_border="#00968F",
    slot_selected_bg_hover="#34B7C1",
    slot_unselected_bg="#FFFFFF",
    slot_unselected_border="#B7C8CE",
    slot_unselected_hover="#F3FBFC",
    badge_pending_bg="#6C757D",
    badge_running_bg="#317ACF",
    badge_success_bg="#00968F",
    badge_error_bg="#D9534F",
)

DARK_THEME = _STYLE_TEMPLATE.format(
    window_bg="#07131C",
    text_primary="#F4F7F8",
    text_muted="#9CB0BA",
    help_text="#76AEEA",
    sidebar_bg="#04101A",
    border_color="#28404D",
    card_bg="#1B2B39",
    button_bg="#223646",
    button_border="#2E4B5A",
    button_hover="#294255",
    button_hover_border="#3DC1CC",
    accent="#00968F",
    input_bg="#091724",
    input_border="#2B4654",
    input_focus_border="#317ACF",
    input_disabled_bg="#142431",
    input_disabled_text="#728590",
    checkbox_border="#4F6977",
    checkbox_bg="#132433",
    scroll_handle="#3A5562",
    scroll_handle_border="#53707C",
    scroll_handle_hover="#3DC1CC",
    slot_selected_bg="#3DC1CC",
    slot_selected_text="#F4F7F8",
    slot_selected_border="#8BE4EA",
    slot_selected_bg_hover="#34B7C1",
    slot_unselected_bg="#0D1C28",
    slot_unselected_border="#34515F",
    slot_unselected_hover="#112432",
    badge_pending_bg="#6C757D",
    badge_running_bg="#317ACF",
    badge_success_bg="#00968F",
    badge_error_bg="#D9534F",
)

APP_STYLE = LIGHT_THEME

def get_app_style(theme_mode: str) -> str:
    return DARK_THEME if theme_mode == "dark" else LIGHT_THEME