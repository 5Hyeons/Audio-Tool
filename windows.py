import os
import glob
import utils
import shutil
import numpy as np
from scipy.io import wavfile
from multiprocessing import Queue

from PyQt5.QtWidgets import *
from PyQt5.QtCore import pyqtSlot

from Threads import *
from player import *


class AudioSplitWindow(QDialog):
    '''원본 오디오 파일을 자르는 클래스입니다.'''
    def __init__(self, w):
        super().__init__(w)
        self.initDialog()
        self.initUI()
        self.initThread()
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
        self.line3 = QLineEdit('-50')
        self.line3.setMaximumWidth(50)
        btn = QPushButton('?')
        btn.setMaximumWidth(20)
        btn.clicked.connect(lambda: self.show_guide(4))
        hbox.addWidget(self.label3)
        hbox.addWidget(self.line3)
        hbox.addWidget(btn)
        vbox.addLayout(hbox)
        # Line 4
        hbox = QHBoxLayout()
        self.label4 = QLabel('Set the offest')
        self.line4 = QLineEdit('1')
        self.line4.setMaximumWidth(50)
        btn = QPushButton('?')
        btn.setMaximumWidth(20)
        btn.clicked.connect(lambda: self.show_guide(5))
        hbox.addWidget(self.label4)
        hbox.addWidget(self.line4)
        hbox.addWidget(btn)
        vbox.addLayout(hbox)
        # Select button
        btn = QPushButton('Select audio file')
        btn.clicked.connect(self.select_audio)
        vbox.addWidget(btn)

        self.setLayout(vbox)

    def initThread(self):
        self.consumer = SplitAudioThread()
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

        self.name = self.line1.text()
        self.min_sil_len = int(self.line2.text())
        self.silence_thresh = int(self.line3.text())
        self.offset = int(self.line4.text())
        print(self.name, self.silence_thresh, self.min_sil_len)

        self.src = QFileDialog.getOpenFileName(self,
                                'Select Audio file to split',
                                '',
                                'Audio (*.wav*)',
                                )[0]

        if self.src is None or self.src == '':
            return
        if os.name == 'nt':
            self.src = self.src.replace('/', '\\')
        self.hide()

        self.pDialog.show()
        self.consumer.setParameters(self.src, self.min_sil_len, self.silence_thresh)
        self.consumer.start()
    
    @pyqtSlot(list)
    def generate_audio(self, audio_chunks):
        '''SplitAudioThread에서 나온 chunks를 저장'''
        dst = os.path.join(os.path.dirname(self.src), self.name)
        os.makedirs(dst, exist_ok=True)

        for i, chunk in enumerate(audio_chunks):
           out_file = os.path.join(dst, f"{self.name}_{i + self.offset:04}.wav")
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
            label.setText('Parameter: 침묵 구간의 기준.\n높을 수록 관용적이고 낮을수록 깐깐합니다.\n(default: -50, 단위 dB)')
        elif n == 5:
            label.setText('파일 생성 시 offset으로 설정한 번호 부터 차례대로 생성됩니다.')
        dialog.show()

    @pyqtSlot(int)
    def set_pbar(self, data):
        self.pbar.setMaximum(data)

    @pyqtSlot(int)
    def update_pbar(self, data):
        self.pbar.setValue(data)

class AudioSplitOneWindow(QDialog):
    '''
    문제 있는 오디오 **하나**를 여러개로 쪼개서 괜찮은 부분만 취하는 Dialog 입니다.
    '''
    def __init__(self, w):
        super().__init__(w)
        self.initUI()
        self.w = w
        self.player = CPlayer(self)
        self.playlist = []
        self.selectedList = []

    def initUI(self):
        self.setWindowTitle('Split one file')
        vbox = QVBoxLayout()
        gb = QGroupBox('splitted list')
        box = QVBoxLayout()
        # Play list
        self.table = QTableWidget(0, 1, self)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setHorizontalHeaderItem(0, QTableWidgetItem('Title'))
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.tableChanged)
        self.table.itemDoubleClicked.connect(self.tableDbClicked)

        box.addWidget(self.table)
        # Line 1
        hbox = QHBoxLayout()
        label = QLabel('Set a minimum length of silence.')
        self.line1 = QLineEdit('800')
        self.line1.setMaximumWidth(50)
        btn = QPushButton('?')
        btn.setMaximumWidth(20)
        btn.clicked.connect(lambda: self.show_guide(3))
        hbox.addWidget(label)
        hbox.addWidget(self.line1)
        hbox.addWidget(btn)
        box.addLayout(hbox)
        # Line 2
        hbox = QHBoxLayout()
        label = QLabel('Set a silent threshold.')
        self.line2 = QLineEdit('-50')
        self.line2.setMaximumWidth(50)
        btn = QPushButton('?')
        btn.setMaximumWidth(20)
        btn.clicked.connect(lambda: self.show_guide(4))
        hbox.addWidget(label)
        hbox.addWidget(self.line2)
        hbox.addWidget(btn)
        box.addLayout(hbox)
        # Select button
        btn = QPushButton('Apply')
        btn.clicked.connect(self.split)
        box.addWidget(btn)

        gb.setLayout(box)
        vbox.addWidget(gb)

        btn = QPushButton('Replace')
        btn.clicked.connect(self.replace)
        vbox.addWidget(btn)

        self.setLayout(vbox)

    def set_file(self, file):
        self.file = file
        self.table.setRowCount(0)

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
        
        if n == 3:
            label.setText('Parameter: 소리 없는 구간의 최소 길이.\n(default: 800, 단위 ms)')
        elif n == 4:
            label.setText('Parameter: 침묵 구간의 기준.\n높을 수록 관용적이고 낮을수록 깐깐합니다.\n(default: -50, 단위 dB)')
        
        dialog.show()

    # 오디오 쪼개기
    def split(self):
        tmp_dir = os.path.join(os.getcwd(), 'temp')
        os.makedirs(tmp_dir, exist_ok=True)
        # 기존 임시 파일 전부 삭제
        [os.remove(path) for path in glob.glob(os.path.join(tmp_dir, '*'))]
        if self.file.endswith('.mp3'):
            seg = utils.AudioSegment.from_mp3(self.file)
        elif self.file.endswith('.wav'):
            seg = utils.AudioSegment.from_wav(self.file)
        else:
            raise ValueError('Not supported file type')
        min_silence_len = int(self.line1.text())
        silence_thresh = int(self.line2.text())
        audio_chunks = utils.split_on_silence(seg, min_silence_len, silence_thresh)
        out_files = []
        file_bn = os.path.basename(self.file)
        for i, chunk in enumerate(audio_chunks):
            out_file = os.path.join(tmp_dir, f'{file_bn[:-4]}_{i+1:02}.wav')
            out_files.append(out_file)
            chunk.export(out_file, format='wav')

        self.createTable(out_files)
        self.createPlaylist(out_files)

    # split 한 파일 원본과 교체
    def replace(self):
        self.player.stop()
        print([self.playlist[s] for s in self.selectedList])
        if len(self.selectedList) == 1:
            print(f'replace [{self.playlist[self.selectedList[0]]}] >>>> [{self.file}]')
            os.remove(self.file)
            shutil.move(self.playlist[self.selectedList[0]], self.file)
        elif len(self.selectedList) > 1:
            os.remove(self.file)
            for i in self.selectedList:
                dst = os.path.join(os.path.dirname(self.file), os.path.basename(self.playlist[i]))
                print(f'move [{self.playlist[i]}] >>>> [{dst}]')
                if os.path.exists(dst):    os.remove(dst)
                shutil.move(self.playlist[i], dst)
        else:
            return
        
        self.close()

    def createPlaylist(self, files):
        self.playlist.clear()
        for file in files:
            self.playlist.append(file)
        self.player.createPlaylist(playlists=self.playlist, option=0)

    def createTable(self, files):
        cnt = len(files)       
        self.table.setRowCount(cnt)
        for i in range(cnt):
            self.table.setItem(i, 0, QTableWidgetItem(os.path.basename(files[i])))

    def updateMediaChanged(self, index):
        if index>=0:
            self.table.selectRow(index)  

    def tableChanged(self):
        self.selectedList.clear()        
        for item in self.table.selectedIndexes():
            self.selectedList.append(item.row())
            
        self.selectedList = list(set(self.selectedList))
            
        if self.table.rowCount()!=0 and len(self.selectedList) == 0:
            self.selectedList.append(0)
    
    def tableDbClicked(self, e):
        self.player.play(startRow=self.selectedList[0])
  
class AudioConcatWindow(QDialog):
    '''
    선택한 오디오 여러개를 하나로 합치는 클래스입니다.
    '''
    def __init__(self, w):
        super().__init__(w)
        self.initUI()
        self.w = w
        self.player = CPlayer(self)
        self.playlist = []
        self.selectedList = []
    

    def initUI(self):
        self.setWindowTitle('Concatenate multiple file')
        vbox = QVBoxLayout()
        gb = QGroupBox('concatenated list')
        box = QVBoxLayout()
        # Play list
        self.table = QTableWidget(0, 1, self)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setHorizontalHeaderItem(0, QTableWidgetItem('Title'))
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.tableChanged)
        self.table.itemDoubleClicked.connect(self.tableDbClicked)

        box.addWidget(self.table)
        # Line 1
        hbox = QHBoxLayout()
        label = QLabel('Set the interval')
        self.line = QLineEdit('500')
        self.line.setMaximumWidth(50)
        btn = QPushButton('?')
        btn.setMaximumWidth(20)
        btn.clicked.connect(self.show_guide)
        hbox.addWidget(label)
        hbox.addWidget(self.line)
        hbox.addWidget(btn)
        box.addLayout(hbox)
        # Select button
        btn = QPushButton('Apply')
        btn.clicked.connect(self.concat)
        box.addWidget(btn)

        gb.setLayout(box)
        vbox.addWidget(gb)

        btn = QPushButton('Replace')
        btn.clicked.connect(self.replace)
        vbox.addWidget(btn)

        self.setLayout(vbox)

    def setup(self, files):
        self.files = files
        self.table.setRowCount(0)
        self.playlist.clear()

        self.tmp_dir = os.path.join(os.getcwd(), 'temp')
        os.makedirs(self.tmp_dir, exist_ok=True)
        # 기존 임시 파일 전부 삭제
        [os.remove(path) for path in glob.glob(os.path.join(self.tmp_dir, '*'))]

    def show_guide(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Guide')

        vbox = QVBoxLayout()
        label = QLabel('연결할 파일들 사이의 간격.')
        btn = QPushButton('OK')
        btn.clicked.connect(dialog.close)
        vbox.addWidget(label)
        vbox.addWidget(btn)
        dialog.setLayout(vbox)
        dialog.show()

    # 오디오 붙이기
    def concat(self):
        # 파일 등록 안돼있으면 리턴
        if not hasattr(self, 'files'):
            return
        
        sil_duration = int(self.line.text()) # ms 단위로 받음
        dst = os.path.join(self.tmp_dir, f'{sil_duration}.wav')
        ys = []
        for src in self.files:
            sr, y = wavfile.read(src)
            if 'sil' not in locals():
                sil = np.zeros(int(sr*sil_duration/1000), dtype=y.dtype)
            
            ys.append(y)
            # if y is streo
            if y.shape[-1] == 2:
                ys.append(np.stack((sil, sil), axis=1))
            else:
                ys.append(sil)
        res = np.vstack(ys[:-1]) if y.shape[-1] == 2 else np.hstack(ys[:-1])
        wavfile.write(dst, sr, res)
        rowPosition = self.table.rowCount()
        self.table.insertRow(rowPosition)
        self.table.setItem(rowPosition, 0, QTableWidgetItem(os.path.basename(dst)))
        self.playlist.append(dst)
        self.player.createPlaylist(playlists=self.playlist, option=0)

    # split 한 파일 원본과 교체
    def replace(self):
        try:
            selectedFile = self.playlist[self.selectedList[0]]
        except IndexError:
            self.player.stop()
            self.close()
            return
        
        for originalFile in self.files:
            print(f'remove {originalFile}')
            os.remove(originalFile)
        print(f'replace [{selectedFile}] >>>> [{self.files[0]}]')
        shutil.move(selectedFile, self.files[0]) 
        
        self.player.stop()
        self.close()
        self.w.addAudioList(refresh=True)
        # self.w.refresh()

    def updateMediaChanged(self, index):
        if index>=0:
            self.table.selectRow(index)  

    def tableChanged(self):
        self.selectedList.clear()        
        for item in self.table.selectedIndexes():
            self.selectedList.append(item.row())
            
        self.selectedList = list(set(self.selectedList))
            
        if self.table.rowCount()!=0 and len(self.selectedList) == 0:
            self.selectedList.append(0)
    
    def tableDbClicked(self, e):
        self.player.play(startRow=self.selectedList[0])


class ProgressDialog(QProgressDialog):
    '''ProgressDialog super class'''
    def __init__(self, w):
        super().__init__(w)
        self.setAutoClose(False)
        self.setAutoReset(False)
        btn = QPushButton("Cancel")
        btn.clicked.connect(self.canceled)
        self.setCancelButton(btn)
        
        self.q = Queue()

    def setThread(self, consumer):
        self.consumer = consumer
        self.consumer.poped.connect(self.update)
        self.consumer.start()

    @pyqtSlot(int)
    def update(self, data):
        self.setValue(data)
        if data == self.maximum():
            self.setCancelButtonText('done')

    def canceled(self):
        self.q.put(0)
        self.close()

# Time measurement dialog
class TimeMeasurementWindow(ProgressDialog):
    '''불러온 오디오 파일들의 전체 길이를 측정하는 클래스.'''
    def __init__(self, w, wavs):
        super().__init__(w)
        self.setWindowTitle(" ")
        self.setLabelText("Measuring time ...")
        self.setRange(0, len(wavs))
        self.setThread(AudioMeasurementThread(wavs, self.q))
        
    @pyqtSlot(int)
    def update(self, data):
        self.setValue(data)
        if data == self.maximum():
            self.setLabelText(f"total time is {round(self.consumer.total_time/60, 3)} m")
            self.setCancelButtonText('done')
    
class AudioTransformWindow(ProgressDialog):
    '''오디오를 44k mono type으로 변환하는 윈도우.'''
    def __init__(self, w, wavs):
        super().__init__(w)
        self.setWindowTitle(" ")
        self.setLabelText("Audio is transforming ...")
        self.setRange(0, len(wavs))
        self.setThread(AudioTransformThread(wavs, self.q))

