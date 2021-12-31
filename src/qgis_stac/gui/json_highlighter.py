

from qgis.PyQt.QtCore import QRegExp, Qt
from qgis.PyQt.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat


class JsonHighlighter(QSyntaxHighlighter):
    """Json Highlighter."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.highlight_rules = []

        text_format = QTextCharFormat()
        pattern = QRegExp("([-0-9.]+)(?!([^\"]*\"[\\s]*\\:))")
        text_format.setForeground(Qt.darkRed)
        self.highlight_rules.append((pattern, text_format))

        text_format = QTextCharFormat()
        pattern = QRegExp("(?:[ ]*\\,[ ]*)(\"[^\"]*\")")
        text_format.setForeground(Qt.darkGreen)
        self.highlight_rules.append((pattern, text_format))

        text_format = QTextCharFormat()
        pattern = QRegExp("(\"[^\"]*\")(?:\\s*\\])")
        text_format.setForeground(Qt.darkGreen)
        self.highlight_rules.append((pattern, text_format))

        text_format = QTextCharFormat()
        pattern = QRegExp("(\"[^\"]*\")\\s*\\:")
        text_format.setForeground(Qt.darkGreen)
        self.highlight_rules.append((pattern, text_format))

        text_format = QTextCharFormat()
        pattern = QRegExp(":+(?:[: []*)(\"[^\"]*\")")
        text_format.setForeground(Qt.darkGreen)
        self.highlight_rules.append((pattern, text_format))

    def highlightBlock(self, text):
        """Highlight of a comment block"""
        for pattern, text_format in self.highlight_rules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)

            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, text_format)
                index = expression.indexIn(text, index + length)
