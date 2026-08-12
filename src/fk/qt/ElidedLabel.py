from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics


class ElidedLabel(QLabel):
    _text: str

    def __init__(self, parent):
        super().__init__(parent)
        self._text = ''
        self.setText('')

    def setText(self, text):
        self._text = text
        self.setToolTip(text)
        self._update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update()

    def _update(self):
        metrics = QFontMetrics(self.font())
        elided = metrics.elidedText(self._text, Qt.TextElideMode.ElideRight, self.width() - 30)
        super().setText(elided)
