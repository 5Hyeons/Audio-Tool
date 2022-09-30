from scipy.io import wavfile

from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QThread, pyqtSignal, pyqtSlot
from multiprocessing import Queue
import time

q = Queue()
# Time measurement dialog
class Measurement(QProgressDialog):
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
        self.consumer = Consumer(wavs)
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
        q.put(0)
        self.close()

# Time measurement thread
class Consumer(QThread):
    poped = pyqtSignal(int)
    def __init__(self, wavs):
        super().__init__()
        self.wavs = wavs
        self.total_time = 0

    def run(self):
        while not q.empty():
            q.get()
        for i, wav in enumerate(self.wavs):
            if not q.empty():
                break
            sr, y = wavfile.read(wav)
            t = len(y)/sr
            self.total_time += t
            self.poped.emit(i+1)
