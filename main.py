# main.py
# -----------------------------------------------------------------------------
# @file     main.py
# @brief    GUI wrapper using QtPy for PythonHeuristicDetector demonstration.
#
# Creates an 800×600 window with two text areas:
#  - Top: enter/paste raw text (“Paste your raw text here”)
#  - Bottom: shows processed result, highlighting <PythonCode>…</PythonCode> in blue.
#
# The bottom area updates live as you edit the top. Quit is available via menu or toolbar.
#
# @author   LoganSeven
# 
# -----------------------------------------------------------------------------

import sys
import re
import html

from qtpy.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QLabel, QTextEdit, QAction, QStyle
)
from qtpy.QtGui import QIcon
from qtpy.QtCore import Qt

# Import the updated detector
from echo_node_system.echo_graph_flow_editor.heuristics.python_heuristic_detector \
    import PythonHeuristicDetector


LOREM = (
    "Avant que vous comptiez dix\n"
    "cette clarté des hautes\n"
    "tout change : le vent ôte\n"
    "tiges de maïs,\n"
    "import numpy as np\n"
    "\n"
    "def regression_parabolique(x, y):\n"
    "    X = np.vstack((x**2, x, np.ones(len(x)))).T\n"
    "    a, b, c = np.linalg.lstsq(X, y, rcond=None)[0]\n"
    "    return a, b, c\n"
    "\n"
    "if __name__ == '__main__':\n"
    "    n = int(input())\n"
    "    xs = list(map(float, input().split()))\n"
    "    ys = list(map(float, input().split()))\n"
    "    xs = np.array(xs)\n"
    "    ys = np.array(ys)\n"
    "    a, b, c = regression_parabolique(xs, ys)\n"
    "    print(a, b, c)\n"
    "Et comme caressée\n"
    "la vaste surface reste\n"
    "éblouie sous ces gestes\n"
    "qui l'avaient peut-être formée.\n"
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Python Heuristic Detector GUI")
        self.resize(800, 600)

        # Central widget + layout
        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        self.setCentralWidget(central)

        # Detector instance
        self.detector = PythonHeuristicDetector()

        # Top label + text area
        top_label = QLabel("Paste your raw text here", self)
        layout.addWidget(top_label)

        self.top_edit = QTextEdit(self)
        self.top_edit.setPlainText(LOREM)
        layout.addWidget(self.top_edit, stretch=1)

        # Bottom label + text area
        bottom_label = QLabel("Processed result", self)
        layout.addWidget(bottom_label)

        self.bottom_edit = QTextEdit(self)
        self.bottom_edit.setReadOnly(True)
        self.bottom_edit.setAcceptRichText(True)
        layout.addWidget(self.bottom_edit, stretch=1)

        # Connect editing signal
        self.top_edit.textChanged.connect(self.update_result)
        self.update_result()

        # File→Exit menu and toolbar
        exit_icon = self.style().standardIcon(QStyle.SP_DialogCloseButton)
        exit_action = QAction(QIcon(exit_icon), "E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)

        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction(exit_action)

        tb = self.addToolBar("Main")
        tb.addAction(exit_action)

    def update_result(self):
        """Re-run the heuristic detector on the top text and display HTML-highlighted."""
        raw = self.top_edit.toPlainText()
        wrapped = self.detector.detectPythonInString(raw)

        # Split by <PythonCode> blocks so we can color them
        parts = re.split(r"(<PythonCode>.*?</PythonCode>)", wrapped, flags=re.DOTALL)
        html_parts = []
        for part in parts:
            if part.startswith("<PythonCode>") and part.endswith("</PythonCode>"):
                # Escape and color blue
                esc = html.escape(part)
                html_parts.append(f'<span style="color: blue;">{esc}</span>')
            else:
                # Plain black
                esc = html.escape(part)
                html_parts.append(esc)

        html_content = "<pre style='font-family: monospace; white-space: pre-wrap;'>"
        html_content += "".join(html_parts)
        html_content += "</pre>"

        self.bottom_edit.setHtml(html_content)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
