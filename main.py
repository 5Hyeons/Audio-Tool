from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import QIcon
from player import *

import sys
import os
import shutil
import random
from jamo import h2j
from glob import glob

from g2pK.g2pkc.g2pk import G2p
from windows import *

QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
 
class CWidget(QWidget):   
 
    def __init__(self):
        super().__init__()
        self.player = CPlayer(self)
        self.playlist = []
        self.selectedList = [0]
        self.playOption = QMediaPlaylist.Sequential
        self.audioDir = None
        self.textFile = None
 
        self.setWindowTitle('오디오 검수 툴')
        self.setWindowIcon(QIcon('AIPARK_logo.png'))
        self.initUI()
 
    def initUI(self):
        self.initGuide()
        vbox = QVBoxLayout()        
 
        # 1.Play List
        box = QVBoxLayout()
        gb = QGroupBox('Play List')
        vbox.addWidget(gb)
         
        self.table = QTableWidget(0, 1, self)   
        header = self.table.horizontalHeader()          
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setHorizontalHeaderItem(0, QTableWidgetItem('Title'))
        # self.table.setHorizontalHeaderItem(1, QTableWidgetItem('Progress')) 
        # read only
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # multi row selection
        # self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        # signal 
        self.table.itemSelectionChanged.connect(self.tableChanged)
        self.table.itemDoubleClicked.connect(self.tableDbClicked)
        # self.table.setAutoScroll(False)
        box.addWidget(self.table)
         
        hbox = QHBoxLayout()
        btnAddAudio = QPushButton('Add Audio')
        btnAddText = QPushButton('Add Text')
        btnAddAudio.clicked.connect(self.addAudioList)
        btnAddText.clicked.connect(self.addTextList)
        hbox.addWidget(btnAddAudio)
        hbox.addWidget(btnAddText)   
        box.addLayout(hbox)
        
        hbox = QHBoxLayout()
        btnSplit = QPushButton('Split')
        btnConcat = QPushButton('Concat')
        btnSplit.clicked.connect(self.audio_split_one)
        btnConcat.clicked.connect(self.audio_concat)
        hbox.addWidget(btnSplit)
        hbox.addWidget(btnConcat)
        box.addLayout(hbox)

        btnRefesh = QPushButton('Refresh')
        btnRefesh.clicked.connect(self.refresh)
        box.addWidget(btnRefesh)
        
        gb.setLayout(box)        

        # 2.Play Control
        box = QHBoxLayout()
        gb = QGroupBox('Play Control')
        vbox.addWidget(gb)
 
        text = ['◀◀', '▶', '■', '▶▶', '사용법']
        grp = QButtonGroup(self)
        for i in range(len(text)):
            btn = QPushButton(text[i], self)            
            grp.addButton(btn, i)
            box.addWidget(btn)
        grp.buttonClicked[int].connect(self.btnClicked)
        gb.setLayout(box)
 
        # 3.Play Option
        box = QHBoxLayout()
        gb = QGroupBox('Play Option')
        vbox.addWidget(gb)       
 
        str = ['current item once', 'current item in loop', 'sequential', 'loop', 'random']
        grp = QButtonGroup(self)
        for i in range(len(str)):
            if i==3: continue # loop 옵션은 안씀
            btn = QRadioButton(str[i], self)
            if i==QMediaPlaylist.Sequential:
                btn.setChecked(True)
            grp.addButton(btn, i)  
            box.addWidget(btn)        
         
        grp.buttonClicked[int].connect(self.radClicked)
             
        gb.setLayout(box)               
        
        # 4.Functions
        gb = QGroupBox('Functions')
        # Buttons of function
        btnAudioSplit = QPushButton('Split')
        btnAudioSplit.setStyleSheet('color:black; font: bold;')
        btnAudioSplit.clicked.connect(self.audio_split)
        btnAudioTransform = QPushButton('Transform')
        btnAudioTransform.setStyleSheet('color:black; font: bold;')
        btnAudioTransform.clicked.connect(self.audio_transform)
        btnTextG2p = QPushButton('G2p Module')
        btnTextG2p.setStyleSheet('color:black; font: bold;')
        btnTextG2p.clicked.connect(self.apply_g2p)
        btnTime = QPushButton('Time')
        btnTime.setStyleSheet('color:black; font:bold;')
        btnTime.clicked.connect(self.time_measurement)
        btnsort = QPushButton('Sorting')
        btnsort.setStyleSheet('color:black; font: bold;')
        btnsort.clicked.connect(self.file_sort_dialog)
        btnDecom = QPushButton('Make filelist')
        btnDecom.setStyleSheet('color:black; font:bold;')
        btnDecom.clicked.connect(self.make_filelist)

        # Function UI

        hbox = QHBoxLayout()
        gb_sub = QGroupBox('audio')
        box = QVBoxLayout()

        hhbox = QHBoxLayout()
        hhbox.addWidget(btnAudioSplit)
        hhbox.addWidget(btnAudioTransform)
        box.addLayout(hhbox)

        hhbox = QHBoxLayout()
        hhbox.addWidget(btnTime)
        hhbox.addWidget(btnsort)
        box.addLayout(hhbox)

        gb_sub.setLayout(box)
        hbox.addWidget(gb_sub)

        gb_sub = QGroupBox('text')
        box = QVBoxLayout()
        box.addWidget(btnTextG2p)
        box.addWidget(btnDecom)
        gb_sub.setLayout(box)
        hbox.addWidget(gb_sub)

        gb.setLayout(hbox)
        vbox.addWidget(gb)

        self.setLayout(vbox)
        self.show()
 
    def initGuide(self):
        self.guideDialog = QDialog(self)
        self.guideDialog.setWindowTitle('Guide')
        self.guideDialog.resize(300, 300)

        self.guideText = QTextEdit('사용법', self.guideDialog)
        self.guideText.resize(290, 250)
        self.guideText.move(5, 5)
        s = '- Delete key\n선택된 파일을 삭제합니다.\n\n- Backspace key\n삭제된 파일을 순서대로 복구합니다.\n\n- Up key\n현재 선택된 칸 위의 칸을 선택합니다.\n\n- Down key\n현재 선택한 칸 아래 칸을 선택합니다.\n\n- Left key\n선택된 파일을 재생합니다.'
        self.guideText.setText(s)
        self.guideText.setReadOnly(True)

        self.guideBtn = QPushButton('OK', self.guideDialog)
        self.guideBtn.move(110, 265)
        self.guideBtn.clicked.connect(lambda: self.guideDialog.close())

    def keyPressEvent(self, event):
        if self.table.rowCount() != 0:
            print(event.key())
            # delete 키 입력 시 제거
            if event.key() == Qt.Key_Delete:
                self.delete()
            # backspace 키 입력 시 복원
            elif event.key() == Qt.Key_Backspace:
                self.restore()
            # 왼쪽 방향키 입력 시 재생
            elif event.key() == Qt.Key_Left:
                self.player.play(self.playlist, self.selectedList[0], self.playOption)
            elif event.key() in [Qt.Key_R, Qt.Key_F5]:
                self.refresh()

    def tableChanged(self):
        self.selectedList.clear()        
        for item in self.table.selectedIndexes():
            self.selectedList.append(item.row())
         
        self.selectedList = list(set(self.selectedList))
         
        if self.table.rowCount()!=0 and len(self.selectedList) == 0:
            self.selectedList.append(0)
 
    def addAudioList(self, refresh=False):
        if not refresh:
            self.audioDir = QFileDialog.getExistingDirectory(self, "Select directory containing audio files")
        if self.audioDir is None or self.audioDir == '':
            return
        self.deleteDir = os.path.join(self.audioDir, 'Deleted')
        
        files = [os.path.join(self.audioDir, file) for file in sorted(os.listdir(self.audioDir)) if '.wav' in file]    

        cnt = len(files)       
        self.table.setRowCount(cnt)
        for i in range(cnt):
            self.table.setItem(i, 0, QTableWidgetItem(files[i]))
            # pbar = QProgressBar(self.table)
            # pbar.setAlignment(Qt.AlignCenter)            
            # self.table.setCellWidget(i,1, pbar)
             
        self.createPlaylist(files)       
 
    def addTextList(self, refresh=False):
        if not refresh: 
            self.textFile = QFileDialog.getOpenFileName(self,
                                            'Select text file',
                                            '',
                                            'Text (*.txt*)',
                                            )   
        if self.textFile is None or self.textFile[0] == '':
            return
        try:
            lines = open(self.textFile[0], 'r', encoding='UTF-8').readlines()
        except UnicodeDecodeError:
            lines = open(self.textFile[0], 'r', encoding='cp949').readlines()

        for i, line in enumerate(lines):
            line = line.rstrip('\n')
            #print(line)
            self.table.setItem(i,0, QTableWidgetItem(line))
            pbar = QProgressBar(self.table)
            pbar.setAlignment(Qt.AlignCenter)            
            self.table.setCellWidget(i,1, pbar)

    # UI 갱신 함수
    def refresh(self):
        self.addAudioList(refresh=True)
        self.addTextList(refresh=True)

    # 오디오 자르는 함수
    def audio_split(self):
        self.hide()
        self.second = AudioSplitWindow()
        self.second.exec()
        self.show()
    def audio_split_one(self):
        if self.audioDir is None or len(self.selectedList) != 1:
            print('Select one')
            return
        selectedFile = self.playlist[self.selectedList[0]]
        print(selectedFile)
        dialog = AudioSplitOneWindow(self, selectedFile)
        dialog.show()
        self.player.stop()
    # 오디오 붙이는 함수
    def audio_concat(self):
        if self.audioDir is None or len(self.selectedList) == 1:
            print('Select multiple files')
            return
        files = sorted([self.playlist[i] for i in self.selectedList])
        print(files)
        dialog = AudioConcatWindow(self, files)
        dialog.show()
        self.player.stop()

    def audio_transform(self):
        pass
    # 시간 측정
    def time_measurement(self):
        if self.audioDir is None or self.audioDir == '':
            return
        wavs = glob(os.path.join(self.audioDir, '*.wav'))
        third = TimeMeasurementWindow(self, wavs)
        third.exec()

    # 파일 정렬
    def file_sort_dialog(self):
        if self.audioDir is None or self.audioDir == '':
            return
        print(self.audioDir)
        self.sort_dialog = QDialog(self)
        self.sort_dialog.setWindowTitle('Audio sort')

        vbox = QVBoxLayout()
        hbox = QHBoxLayout()
        label = QLabel('file name')
        label2 = QLabel('offset')
        hbox.addWidget(label)
        hbox.addWidget(label2)
        vbox.addLayout(hbox)

        hbox = QHBoxLayout()
        self.sort_line = QLineEdit('split')
        self.sort_offset = QLineEdit('1')
        hbox.addWidget(self.sort_line)
        hbox.addWidget(self.sort_offset)
        vbox.addLayout(hbox)

        btn = QPushButton('OK')
        btn.clicked.connect(self.file_sort)
        vbox.addWidget(btn)

        self.sort_dialog.setLayout(vbox)
        self.sort_dialog.show()

    def file_sort(self):
        wavs = sorted(glob(os.path.join(self.audioDir, '*.wav')))
        if os.path.exists(self.deleteDir):
            shutil.rmtree(self.deleteDir)
        name = self.sort_line.text()
        offset = int(self.sort_offset.text()) if self.sort_offset.text().isdigit() else 1
        for i, path in enumerate(wavs):
            os.rename(path, f'{self.audioDir}/{name}_{i+offset:04}.wav')
        self.sort_dialog.close()
        self.refresh()

    # Apply g2p module
    def apply_g2p(self):
        textFile = QFileDialog.getOpenFileName(self,
                                        'Select text file',
                                        '',
                                        'Text (*.txt*)',
                                        )[0]
        if textFile == '':
            return
        dir, bn = os.path.split(textFile)
        name, ext = os.path.splitext(bn)
        new_textFile = os.path.join(dir, name + '_cleand' + ext)
        g2p = G2p()
        with open(new_textFile, 'w', encoding='utf-8') as f:
            lines = open(textFile, 'r', encoding='utf-8').read()
            lines_g2p = g2p(lines, descriptive=True, to_syl=True, use_dict=True)
            lines_g2p = lines_g2p.replace('*', '')
            f.write(lines_g2p)

    # phoneme to jamo
    def make_filelist(self):
        if self.audioDir is None or self.audioDir == '' or self.textFile is None or self.textFile[0] == '':
            return
        name = os.path.basename(self.audioDir)
        dst_train = os.path.join(os.path.dirname(self.audioDir), 'train_filelist.txt.cleaned')
        dst_valid = os.path.join(os.path.dirname(self.audioDir), 'valid_filelist.txt.cleaned')
        
        wavs = sorted(glob(os.path.join(self.audioDir, '*.wav')))
        lines = open(self.textFile[0], 'r', encoding='UTF-8').readlines()
        random.seed(1997)
        valid_idxs = random.sample(range(len(lines)), min(10, len(lines)//10))

        with open(dst_train, 'w', encoding='utf-8') as t, open(dst_valid, 'w', encoding='utf-8') as v:
            for i in range(len(lines)):
                filename = os.path.basename(wavs[i])
                line = lines[i]
                line = h2j(line.rstrip('\n'))
                new_line = f'{name}/{filename}|0|{line}\n'
                if i in valid_idxs:
                    v.write(new_line)
                else:
                    t.write(new_line)

    # 파일 삭제
    def delete(self):
        '''
        현재 선택되어 있는 아이템들을 전부 삭제합니다.
        삭제 키로 파일 삭제 시 파일을 제거(remove)하는 것이 아닌 Deleted 폴더로 옮기는 방식을 사용했습니다.
        따라서 필요 시 복원이 가능하며, 제거한 역순으로의 복원을 위해 Deleted 폴더로 옮길 때 원본에 숫자 태그를 붙여 옮깁니다.        
        '''
        os.makedirs(self.deleteDir, exist_ok=True)
        if len(self.selectedList) > 1 or self.selectedList[0] == 0:
            _index = min(self.selectedList) 
        else: 
            _index = self.selectedList[0]-1

        for _item in self.selectedList:
            selectedFile = self.playlist[_item]
            fileName = os.path.basename(selectedFile)
            # 숫자 태그 붙이기
            newFileName = f'{len(os.listdir(self.deleteDir))+1}_{fileName}'
            # 제거
            shutil.move(selectedFile, os.path.join(self.deleteDir, newFileName))
            print(selectedFile, 'is deleted')   
        # UI 갱신
        self.refresh()
        self.updateMediaChanged(_index)
    # 삭제한 파일 되돌리는 함수
    def restore(self):
        '''
        삭제한 파일들은 기존의 이름 앞에 숫자 태그가 붙은 채로 전부 Deleted 폴더에 보관되어 있습니다.
        파일 앞에 붙어 있는 숫자태그를 바탕으로 가장 최근의 삭제된 파일을 복원합니다.
        복원 시 숫자 태그를 제거함으로써 원래 이름으로 돌아옵니다.
        '''
        if not os.path.exists(self.deleteDir):
            return
        # 숫자 태그 기준으로 sort
        deletedFiles = sorted(glob(os.path.join(self.deleteDir, '*.wav')), key=lambda x: int(os.path.basename(x).split('_')[0]))
        if not deletedFiles:
            return
        filename = os.path.basename(deletedFiles[-1])
        # 숫자 태그 제거
        newFilename = filename[filename.find('_')+1:]
        # 복원
        shutil.move(deletedFiles[-1], os.path.join(os.path.dirname(self.deleteDir), newFilename))
        # UI 화면 갱신
        self.refresh()
        self.updateMediaChanged(self.selectedList[0])

    def btnClicked(self, id):
        if id==0:   #◀◀
            self.player.prev()
        elif id==1: #▶
            if self.table.rowCount()>0:
                self.player.play(self.playlist, self.selectedList[0], self.playOption)
        elif id==2: #■
            self.player.stop()
        elif id==3: #▶▶
            self.player.next()
        elif id==4:
            self.guideDialog.show()
 
    def tableDbClicked(self, e):
        self.player.play(self.playlist, self.selectedList[0], self.playOption)
 
    def volumeChanged(self):
        self.player.upateVolume(self.slider.value())
 
    def radClicked(self, id):
        self.playOption = id
        self.player.updatePlayMode(id)
 
    def paintEvent(self, e):
        self.table.setColumnWidth(0, self.table.width()*0.7)
        self.table.setColumnWidth(1, self.table.width()*0.2)
 
    def createPlaylist(self, files):
        self.playlist.clear()
        for file in files:
            self.playlist.append(file)
 
    def updateMediaChanged(self, index):
        if index>=0:
            self.table.selectRow(index)            
 
 
if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = CWidget()
    sys.exit(app.exec_())
