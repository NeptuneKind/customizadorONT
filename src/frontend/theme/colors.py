APP_STYLE = """
QMainWindow {
    background: #0F172A;
}

QWidget {
    color: #E5E7EB;
    font-size: 13px;
}

QWidget#sidebar {
    background: #111827;
    border-right: 1px solid #334155;
}

QLabel#sidebarTitle {
    font-size: 22px;
    font-weight: 700;
    color: #E5E7EB;
}

QLabel#sidebarSubtitle {
    font-size: 12px;
    color: #94A3B8;
}

QFrame[card="true"], QWidget[card="true"] {
    background: #1F2937;
    border: 1px solid #334155;
    border-radius: 18px;
}

QLabel[cardTitle="true"] {
    font-size: 18px;
    font-weight: 700;
    color: #E5E7EB;
}

QLabel[cardSubtitle="true"] {
    font-size: 12px;
    color: #94A3B8;
}

QPushButton {
    background: #243041;
    color: #E5E7EB;
    border: 1px solid #334155;
    border-radius: 10px;
    min-height: 40px;
    padding: 8px 12px;
}

QPushButton:hover {
    background: #334155;
}

QPushButton[active="true"] {
    background: #2563EB;
    border: 1px solid #2563EB;
}

QPushButton[slotSelected="true"] {
    background: #2563EB;
    border: 2px solid #FFFFFF;
}

QPushButton[slotSelected="false"] {
    background: #243041;
    border: 1px solid #334155;
}

QLineEdit, QComboBox, QTextEdit, QPlainTextEdit {
    background: #0B1220;
    color: #E5E7EB;
    border: 1px solid #3B82F6;
    border-radius: 10px;
    min-height: 38px;
    padding: 6px 10px;
}

QLineEdit:disabled, QComboBox:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {
    background: #1E293B;
    color: #6B7280;
    border: 1px solid #334155;
}

QLabel[muted="true"] {
    color: #94A3B8;
}

QLabel[badge="pending"] {
    background: #64748B;
    color: #FFFFFF;
    border-radius: 12px;
    padding: 6px 12px;
}

QLabel[badge="running"] {
    background: #38BDF8;
    color: #FFFFFF;
    border-radius: 12px;
    padding: 6px 12px;
}

QLabel[badge="success"] {
    background: #22C55E;
    color: #FFFFFF;
    border-radius: 12px;
    padding: 6px 12px;
}

QLabel[badge="error"] {
    background: #EF4444;
    color: #FFFFFF;
    border-radius: 12px;
    padding: 6px 12px;
}

QCheckBox {
    spacing: 10px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 9px;
    border: 1px solid #334155;
    background: #243041;
}

QCheckBox::indicator:checked {
    background: #2563EB;
    border: 1px solid #2563EB;
}
"""