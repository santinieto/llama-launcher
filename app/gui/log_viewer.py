from __future__ import annotations

import html
from collections import deque

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import QTextBrowser, QVBoxLayout, QWidget


class LogViewer(QWidget):
    MAX_LINES = 500

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._buffer: deque[str] = deque(maxlen=self.MAX_LINES)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._text = QTextBrowser()
        self._text.setOpenExternalLinks(False)
        self._text.setFont(QFont("Cascadia Code", 9))
        # Fallback a Consolas si Cascadia no está
        if self._text.font().family() != "Cascadia Code":
            self._text.setFont(QFont("Consolas", 9))
        self._text.setStyleSheet("""
            QTextBrowser {
                background-color: #0a0a14;
                color: #d4d4d4;
                border: 1px solid #1e1e2e;
                border-radius: 8px;
                padding: 8px;
                selection-background-color: #2a2a4a;
                selection-color: #fff;
            }
            QScrollBar:vertical {
                background: #0a0a14;
                width: 8px;
                margin: 2px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #2a2a3a;
                border-radius: 4px;
                min-height: 24px;
            }
            QScrollBar::handle:vertical:hover { background: #3a3a5a; }
            QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
        """)
        layout.addWidget(self._text)

    def append_line(self, line: str) -> None:
        self._buffer.append(line)
        esc = html.escape(line)
        # Colorear según contenido
        lower = line.lower()
        if "error" in lower or "✖" in line or "falta" in lower or "failed" in lower:
            self._text.append(f'<span style="color:#ff6b6b;">{esc}</span>')
        elif "listening" in lower or "✓" in line or "listo" in lower or "running" in lower:
            self._text.append(f'<span style="color:#4caf50;">{esc}</span>')
        elif "[system]" in lower or "[ui]" in lower:
            self._text.append(f'<span style="color:#7aafff;">{esc}</span>')
        elif "starting" in lower or "iniciando" in lower:
            self._text.append(f'<span style="color:#ffb74d;">{esc}</span>')
        else:
            self._text.append(esc)
        cursor = self._text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self._text.setTextCursor(cursor)

    def clear(self) -> None:
        self._buffer.clear()
        self._text.clear()

    def get_buffer(self) -> list[str]:
        return list(self._buffer)
