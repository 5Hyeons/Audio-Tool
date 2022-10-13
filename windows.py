import os
from multiprocessing import Queue

from PyQt5.QtWidgets import *
from PyQt5.QtCore import pyqtSlot

from Threads import Measurement, SplitAudio

class AudioSplitWindow(QDialog, QWidget):
    def __init__(self):
        super().__init__()
        self.initDialog()
        self.initUI()
        self.initThread()
        self.show()
        self.text = ''

    def initUI(self):
        self.setWindowTitle('Audio Split Tool')
        self.resize(340, 150)

        vbox = QVBoxLayout()
        # Line 1
        hbox = QHBoxLayout()
        self.label1 = QLabel('Name the files')
        self.line1 = QLineEdit('split')
        self.line1.setMaximumWidth(50)
        btn = QPushButton('?')
        btn.setMaximumWidth(20)
        btn.clicked.connect(lambda: self.show_guide(2))
        hbox.addWidget(self.label1)
        hbox.addWidget(self.line1)
        hbox.addWidget(btn)
        vbox.addLayout(hbox)
        # Line 2
        hbox = QHBoxLayout()
        self.label2 = QLabel('Set a minimum length of silence.')
        self.line2 = QLineEdit('1200')
        self.line2.setMaximumWidth(50)
        btn = QPushButton('?')
        btn.setMaximumWidth(20)
        btn.clicked.connect(lambda: self.show_guide(3))
        hbox.addWidget(self.label2)
        hbox.addWidget(self.line2)
        hbox.addWidget(btn)
        vbox.addLayout(hbox)
        # Line 3
        hbox = QHBoxLayout()
        self.label3 = QLabel('Set a silent threshold.')
        self.line3 = QLineEdit('45')
        self.line3.setMaximumWidth(50)
        btn = QPushButton('?')
        btn.setMaximumWidth(20)
        btn.clicked.connect(lambda: self.show_guide(4))
        hbox.addWidget(self.label3)
        hbox.addWidget(self.line3)
        hbox.addWidget(btn)
        vbox.addLayout(hbox)
        # Select button
        btn = QPushButton('Select audio file')
        btn.clicked.connect(self.select_audio)
        vbox.addWidget(btn)

        self.setLayout(vbox)

    def initThread(self):
        self.consumer = SplitAudio()
        self.consumer.poped.connect(self.generate_audio)
        self.consumer.maxValue.connect(self.set_pbar)
        self.consumer.curValue.connect(self.update_pbar)

    def initDialog(self):
        # progressbar Dialog
        self.pDialog = QDialog(self)
        self.pDialog.setWindowTitle('wait for a few minutes ...')
        # self.pDialog.setWindowModality(Qt.NonModal)
        self.pDialog.resize(320, 60)
        vbox = QVBoxLayout()
        self.pbar = QProgressBar()
        self.pbar.setRange(0, 0)
        vbox.addWidget(self.pbar)
        self.pDialog.setLayout(vbox)

    def select_audio(self):
        self.hide()

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

        self.pDialog.show()
        self.consumer.setParameters(self.src, self.min_sil_len, self.silence_thresh)
        self.consumer.start()
    
    @pyqtSlot(list)
    def generate_audio(self, audio_chunks):
        dst = os.path.join(os.path.dirname(self.src), self.name)
        os.makedirs(dst, exist_ok=True)

        for i, chunk in enumerate(audio_chunks):
           out_file = os.path.join(dst, f"{self.name}_{i+1:04}.wav")
           chunk.export(out_file, format="wav")
        print(1+i, os.path.basename(self.src))
        del audio_chunks

        self.pDialog.close()
        self.change_dialog(dst)

    def change_dialog(self, dst):
        dialog = QDialog(self)

        dialog.setWindowTitle('Audio Split is complete')
        vbox = QVBoxLayout()
        label = QLabel('It wavs split into {} files in '.format(len(os.listdir(dst))))
        te = QTextEdit(dst)
        te.setReadOnly(True)
        btn = QPushButton('Done')
        btn.clicked.connect(dialog.close)
        btn.clicked.connect(self.close)
        vbox.addWidget(label)
        vbox.addWidget(te)
        vbox.addWidget(btn) 
        dialog.setLayout(vbox)

        dialog.show()

    def show_guide(self, n):
        dialog = QDialog(self)
        dialog.setWindowTitle('Guide')

        vbox = QVBoxLayout()
        label = QLabel()
        btn = QPushButton('OK')
        btn.clicked.connect(dialog.close)
        vbox.addWidget(label)
        vbox.addWidget(btn)
        dialog.setLayout(vbox)
        
        if n == 2:
            label.setText('split 한 후 오디오 파일들의 이름을 정하세요.\n(default: split)')
        elif n == 3:
            label.setText('Parameter: 소리 없는 구간의 최소 길이.\n(default: 1200, 단위 ms)')
        elif n == 4:
            label.setText('Parameter: 침묵 구간의 기준.\n낮을 수록 관용적이고 높을수록 깐깐합니다.\n(default: 45, 단위 dB)')
        
        dialog.show()

    @pyqtSlot(int)
    def set_pbar(self, data):
        self.pbar.setMaximum(data)

    @pyqtSlot(int)
    def update_pbar(self, data):
        self.pbar.setValue(data)


# Time measurement dialog
class TimeMeasurementWindow(QProgressDialog):
    def __init__(self, w, wavs):
        super().__init__(w)
        self.setWindowTitle(" ")
        self.setLabelText("Measuring time ...")
        self.setRange(0, len(wavs))
        self.setAutoClose(False)
        self.setAutoReset(False)
        btn = QPushButton("Cancle")
        btn.clicked.connect(self.canceled)
        self.setCancelButton(btn)
        
        self.q = Queue()
        self.consumer = Measurement(wavs, self.q)
        self.consumer.poped.connect(self.update)
        self.consumer.start()
        
    @pyqtSlot(int)
    def update(self, data):
        print(data)
        self.setValue(data)
        if data == self.maximum():
            self.setLabelText(f"total time is {self.consumer.total_time//60} m")
            self.setCancelButtonText('done')
    
    def canceled(self):
        self.q.put(0)
        self.close()
