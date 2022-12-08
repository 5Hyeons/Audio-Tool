from PyQt5.QtWidgets import *

class TextEditor(QWidget):
    '''
    검수 대본 편집을 위한 텍스트 편집기.
    현재 1, 2로 나뉘며 1은 일반 대본, 2는 g2p로 변환한 대본입니다.
    '''
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        vbox = QVBoxLayout()
        self.textEdit = QTextEdit()
        self.textEdit.setLineWrapMode(QTextEdit.NoWrap)
        self.textEdit.setUndoRedoEnabled(True)
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

def makeHboxLayout(*widgets):
    hbox = QHBoxLayout()
    for widget in widgets:
        hbox.addWidget(widget)
    return hbox