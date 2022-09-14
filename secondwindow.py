import os
import sys
from pydub import AudioSegment
from pydub.silence import split_on_silence

from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt

class secondwindow(QDialog, QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.show()
        self.text = ''

    def initUI(self):
        self.setWindowTitle('Audio Split Tool')
        self.resize(340, 140)
        self.initDialog()
        self.initLine()
        self.initLable()
        self.initBtn()

    def initLine(self):
        self.line1 = QLineEdit(self)
        self.line1.move(260, 20)
        self.line1.resize(50,20)
        self.line1.setText('split')
        self.line1.setAlignment(Qt.AlignRight)

        self.line2 = QLineEdit(self)
        self.line2.move(260, 50)
        self.line2.resize(50,20)
        self.line2.setText('1200')
        self.line2.setAlignment(Qt.AlignRight)

        self.line3 = QLineEdit(self)
        self.line3.move(260, 80)
        self.line3.resize(50,20)
        self.line3.setText('45')
        self.line3.setAlignment(Qt.AlignRight)

    def initLable(self):
        self.label1 = QLabel(self)
        self.label1.move(10, 20)
        self.label1.resize(300, 20)
        self.label1.setText('choose files name')
        self.label1.setAlignment(Qt.AlignLeft)
        self.label1.setStyleSheet('color:black; font: bold;')

        self.label2 = QLabel(self)
        self.label2.move(10, 50)
        self.label2.resize(300, 20)
        self.label2.setText('choose minimum silence length')
        self.label2.setAlignment(Qt.AlignLeft)
        self.label2.setStyleSheet('color:black; font: bold;')

        self.label3 = QLabel(self)
        self.label3.move(10, 80)
        self.label3.resize(300, 20)
        self.label3.setText('choose silence threshold')
        self.label3.setAlignment(Qt.AlignLeft)
        self.label3.setStyleSheet('color:black; font: bold;')

        self.glabel = QLabel(self.gDialog)
        self.glabel.setAlignment(Qt.AlignLeft)
        self.glabel.move(10, 30)
        self.glabel.resize(300, 60)
        

    def initBtn(self):
        self.btn1 = QPushButton('Select audio file', self)
        self.btn1.move(110, 110)
        self.btn1.clicked.connect(self.select_audio)

        self.btn2 = QPushButton('?', self)
        self.btn2.move(320, 20)
        self.btn2.resize(15,20)
        self.btn2.clicked.connect(lambda: self.show_guide(2))

        self.btn3 = QPushButton('?', self)
        self.btn3.move(320, 50)
        self.btn3.resize(15,20)
        self.btn3.clicked.connect(lambda: self.show_guide(3))

        self.btn4 = QPushButton('?', self)
        self.btn4.move(320, 80)
        self.btn4.resize(15,20)
        self.btn4.clicked.connect(lambda: self.show_guide(4))

        self.gbtn = QPushButton('OK', self.gDialog)
        self.gbtn.move(130, 110)
        self.gbtn.clicked.connect(lambda: self.gDialog.close())

    def initDialog(self):
        # progressbar Dialog
        self.pDialog = QDialog()
        self.pDialog.setWindowTitle('wait for a few minutes ...')
        self.pDialog.setWindowModality(Qt.NonModal)
        self.pDialog.resize(320, 60)
        # guide Dialog
        self.gDialog = QDialog()
        self.gDialog.setWindowTitle('Guide')
        self.gDialog.resize(340, 140)

    def select_audio(self):
        self.name = self.line1.text()
        self.min_sil_len = int(self.line2.text())
        self.silence_thresh = -int(self.line3.text())
        print(self.name, self.silence_thresh, self.min_sil_len)

        self.src = QFileDialog.getOpenFileName(self,
                                'Select Audio file to split',
                                '',
                                'Audio (*.wav*)',
                                )[0]

        if self.src is None or self.src == '':
            return
        elif os.name == 'nt':
            self.src = self.src.replace('/', '\\')

        self.split_audio()
        self.change_dialog()

    def split_audio(self):
        pbar = QProgressBar(self.pDialog)
        pbar.move(10, 20)
        pbar.resize(300, 20)
        pbar.setMinimum(0)
        pbar.setMaximum(0)

        self.pDialog.show()
        
        self.dst = os.path.join(os.path.dirname(self.src), 'split')
        os.makedirs(self.dst, exist_ok=True)

        sound_file = AudioSegment.from_wav(self.src)
        audio_chunks = split_on_silence(sound_file, min_silence_len=self.min_sil_len, silence_thresh=self.silence_thresh)  # 조정 필
        
        for i, chunk in enumerate(audio_chunks):
           out_file = os.path.join(self.dst, f"{self.name}_{i+1:04}.wav")
           chunk.export(out_file, format="wav")
        print(1+i, os.path.basename(self.src))
        del audio_chunks, sound_file

        self.pDialog.close()

    def change_dialog(self):
        self.setWindowTitle('Audio Split is complete')

        self.label1.setText('It was split into ')
        self.label2.setText('{} files in '.format(len(os.listdir(self.dst))))
        self.label3.setText(self.dst)

        self.line1.hide()
        self.line2.hide()
        self.line3.hide()

        self.btn1.setText('done')
        self.btn1.disconnect()
        self.btn1.clicked.connect(lambda x: self.close())

    def show_guide(self, n):
        if n == 2:
            self.glabel.setText('split 한 후 오디오 파일들의 이름을 정하세요.\n(default: split)')
        elif n == 3:
            self.glabel.setText('Parameter: 소리 없는 구간의 최소 길이.\n(default: 1200, 단위 ms)')
        elif n == 4:
            self.glabel.setText('Parameter: 침묵 구간의 기준.\n낮을 수록 관용적이고 높을수록 깐깐합니다.\n(default: 45, 단위 dB)')
        
        self.gDialog.show()