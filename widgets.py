from PyQt5.QtWidgets import *

class TextEditor(QWidget):
    
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        vbox = QVBoxLayout()
        self.textEdit = QTextEdit()
        self.textEdit.setLineWrapMode(QTextEdit.NoWrap)
        vbox.addWidget(self.textEdit)

        hbox = QHBoxLayout()
        btnZoomIn = QPushButton('Zoom In')
        btnZoomOut = QPushButton('Zoom Out')
        btnZoomIn.clicked.connect(lambda: self.zoom(True))
        btnZoomOut.clicked.connect(lambda: self.zoom(False))
        hbox.addWidget(btnZoomIn)
        hbox.addWidget(btnZoomOut)
        vbox.addLayout(hbox)

        self.setLayout(vbox)

    def zoom(self, event):
        if event:
            self.textEdit.zoomIn(1)
        else:
            self.textEdit.zoomOut(1)

