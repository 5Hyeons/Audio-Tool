from bisect import bisect
from hashlib import new
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import QIcon, QColor, QTextCursor
from player import *
from widgets import *

import sys
import os
import time
import shutil
import random
import bisect
import glob
from jamo import h2j

from g2pK.g2pkc.g2pk import G2p
from windows import *

QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
 
class CWidget(QWidget):   
 
    def __init__(self):
        super().__init__()
        self.player = CPlayer(self)
        self.playlist = []
        self.selectedList = [0]
        self.lastSelectedLine = 0
        self.playOption = QMediaPlaylist.Sequential
 
        self.setWindowTitle('TTS Data Tool')
        self.setWindowIcon(QIcon('AIPARK_logo.png'))
        self.initUI()

 
    def initUI(self):
        self.initDialog()
        vbox = QVBoxLayout()        
 
        # 1.Play List
        gb = QGroupBox('Play List')
        vbox.addWidget(gb)
         
        box = QVBoxLayout()
        hbox = QHBoxLayout()
        self.table = QTableWidget(0, 1, self) 
        # override key event
        self.table.keyPressEvent = self.keyPressTable
        header = self.table.horizontalHeader()          
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setHorizontalHeaderItem(0, QTableWidgetItem('Title'))
        # self.table.setHorizontalHeaderItem(1, QTableWidgetItem('Progress')) 
        # read only
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # multi row selection
        # self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        # 선택 바뀌면 self.selectedList 갱신
        self.table.itemSelectionChanged.connect(self.tableChanged)
        # 더블 클릭 시 재생
        self.table.itemDoubleClicked.connect(self.tableDbClicked)
        hbox.addWidget(self.table)
        # show editor1, 2와 연결
        self.textEditors = [TextEditor(), TextEditor()]
        self.textEditors[0].hide()
        self.textEditors[1].hide()
        hbox.addWidget(self.textEditors[0])
        hbox.addWidget(self.textEditors[1])
        box.addLayout(hbox)
        
        hbox = QHBoxLayout()
        gb_sub = QGroupBox()
        vvbox = QVBoxLayout()

        # 오디오 리스트 추가 (폴더 선택)
        btnAddAudio = QPushButton('Add Audio')
        btnAddAudio.clicked.connect(self.addAudioList)
        vvbox.addWidget(btnAddAudio)
        
        # split and concat func
        hhbox = QHBoxLayout()
        btnSplit = QPushButton('Split')
        btnConcat = QPushButton('Concat')
        btnSplit.clicked.connect(self.audio_split_one)
        btnConcat.clicked.connect(self.audio_concat)

        hhbox.addWidget(btnSplit)
        hhbox.addWidget(btnConcat)
        vvbox.addLayout(hhbox)
        gb_sub.setLayout(vvbox)
        hbox.addWidget(gb_sub)

        gb_sub = QGroupBox()
        vvbox = QVBoxLayout()

        btnAddText = QPushButton('Add Text')
        btnAddText.clicked.connect(self.addTextList)
        vvbox.addWidget(btnAddText)   

        hhbox = QHBoxLayout()
        self.btnShowEditor1 = QPushButton('Show Editor 1')
        self.btnShowEditor1.setCheckable(True)
        self.btnShowEditor2 = QPushButton('Show Editor 2')
        self.btnShowEditor2.setCheckable(True)
        
        self.btnShowEditor1.clicked.connect(lambda: self.textEditors[0].show() if self.btnShowEditor1.isChecked() else self.textEditors[0].hide())
        self.btnShowEditor2.clicked.connect(lambda: self.addAdditionalText(self.btnShowEditor2.isChecked()))
        self.btnShowEditor2.clicked.connect(lambda: self.textEditors[1].show() if self.btnShowEditor2.isChecked() else self.textEditors[1].hide())

        hhbox.addWidget(self.btnShowEditor1)
        hhbox.addWidget(self.btnShowEditor2)
        vvbox.addLayout(hhbox)
        gb_sub.setLayout(vvbox)
        hbox.addWidget(gb_sub)
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
        btnDecom.clicked.connect(self.make_filelist_dialog)

        # Function UI
        hbox = QHBoxLayout()
        gb_sub = QGroupBox()
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

        gb_sub = QGroupBox()
        box = QVBoxLayout()
        box.addWidget(btnTextG2p)
        box.addWidget(btnDecom)
        gb_sub.setLayout(box)
        hbox.addWidget(gb_sub)

        gb.setLayout(hbox)
        vbox.addWidget(gb)

        statusbar = QStatusBar()
        statusbar.showMessage('made by hans')
        vbox.addWidget(statusbar)

        self.setLayout(vbox)
        self.show()
 
    def initDialog(self):
        # Audio Split One Window
        self.AudioSplitWindow = AudioSplitWindow(self)
        self.AudioSplitOneWindow = AudioSplitOneWindow(self)
        self.AudioConcatWindow = AudioConcatWindow(self)
        # guide dialog
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
        # sort dialog
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
        # filelist dialog
        self.filelist_dialog = QDialog(self)
        self.filelist_dialog.setWindowTitle('Make filelist')

        vbox = QVBoxLayout()
        hbox = QHBoxLayout()
        self.filelist_ckboxes = [QCheckBox('G2p'), QCheckBox('jamo'), QCheckBox('Validation')]
        for ckbox in self.filelist_ckboxes:
            hbox.addWidget(ckbox)
        vbox.addLayout(hbox)
        
        label = QLabel('character :')
        self.character = QLineEdit()
        self.character.setMaximumWidth(130)
        vbox.addLayout(makeHboxLayout(label, self.character))

        label = QLabel('filename  :')
        self.filelist_name = QLineEdit('filelist.txt')
        self.filelist_name.setMaximumWidth(130)
        vbox.addLayout(makeHboxLayout(label, self.filelist_name))

        btn = QPushButton('OK')
        btn.clicked.connect(self.make_filelist)
        vbox.addWidget(btn)
        self.filelist_dialog.setLayout(vbox)

    def keyPressTable(self, event):
        print(event.key())
        # 위로 가기, 아래로 가기
        if event.key() == Qt.Key.Key_Up:
            QTableWidget.keyPressEvent(self.table, event)
        elif event.key() == Qt.Key.Key_Down:
            QTableWidget.keyPressEvent(self.table, event)
        # 0~9 숫자 키 입력 시
        elif event.key() in range(48, 58, 1):
            character = event.key()-48
            print('press ', character)
            # text editor에 마킹
            self.insertCharacter(self.textEditors, self.selectedList[0], character)
        else:
            super().keyPressEvent(event)

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
                self.player.play(startRow=self.selectedList[0])
            # open the text editor1
            elif event.key() == Qt.Key_Right:
                if self.btnShowEditor1.isChecked():
                    self.textEditors[0].hide()  
                    self.btnShowEditor1.setChecked(False)
                else:
                    self.btnShowEditor1.setChecked(True)
                    self.textEditors[0].show() 
            # F5키 입력 시 새로고침
            elif event.key() in [Qt.Key_R, Qt.Key_F5]:
                self.refresh()
            # F4키 입력
            elif event.key() == Qt.Key_F4:
                # 재생 중이면 중지
                if self.player.state() == QMediaPlayer.State.PlayingState:
                    self.player.stop()
                # Editor가 열려있는 경우 커서 위치의 파일 재생, Editor 둘 다 열려있는 경우 첫 번째 것을 따름.
                elif self.btnShowEditor1.isChecked():
                    blockNumber = self.textEditors[0].textEdit.textCursor().blockNumber()
                    self.player.play(startRow=blockNumber)
                elif self.btnShowEditor2.isChecked():
                    blockNumber = self.textEditors[1].textEdit.textCursor().blockNumber()
                    self.player.play(startRow=blockNumber)
                else:
                    self.player.play(startRow=self.selectedList[0])

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
            if os.name == 'nt':
                self.audioDir = self.audioDir.replace('/', '\\')
            self.deleteDir = os.path.join(self.audioDir, 'Deleted')
        if not hasattr(self, 'audioDir') or self.audioDir == '':
            return
        
        files = [os.path.join(self.audioDir, file) for file in sorted(os.listdir(self.audioDir)) if '.wav' in file]    

        last_selection = self.selectedList[0]
        cnt = len(files)       
        self.table.setRowCount(cnt)
        if not refresh:
            for i in range(cnt):
                self.table.setItem(i, 0, QTableWidgetItem(files[i]))
        self.createPlaylist(files=files)
        self.selectedList = [last_selection]
        self.updateMediaChanged(last_selection)    
 
    def addTextList(self, refresh=False):
        '''
        refresh가 True인 경우는 textEditor[0]에서 수정하고 업데이트 키(F5)를 누르거나 버튼을 누르는 경우가 있습니다.
        이 때는 원래 가지고 있던 textFile 경로를 재사용합니다.
        '''
        if not refresh: 
            self.textFile = QFileDialog.getOpenFileName(self,
                                            'Select text file',
                                            '',
                                            'Text (*.txt*)',
                                            )   
        # self.textFile 변수 자체가 없거나 있어도 내용이 없는 경우
        if not hasattr(self, 'textFile') or self.textFile[0] == '':
            return
        try:
            lines = open(self.textFile[0], 'r', encoding='UTF-8').readlines()
        except UnicodeDecodeError:
            lines = open(self.textFile[0], 'r', encoding='cp949').readlines()
        # 파일리스트 예외 처리
        if 'filelist' in self.textFile[0]:
            lines = [line.split('|')[-1] for line in lines]
        # 메인 테이블 갱신
        for i, line in enumerate(lines):
            line = line.rstrip('\n')
            self.table.setItem(i, 0, QTableWidgetItem(line))

        if not refresh:
            self.textEditors[0].textEdit.setText(''.join(lines))

    def addAdditionalText(self, checked):
        '''
        cleaned 텍스트 파일을 담는 editor2를 추가하는 부분입니다.
        '''
        if not checked: return
        self.textFile2 = QFileDialog.getOpenFileName(self,
                                    'Select additional text',
                                    '',
                                    'Text (*.txt*)',
                                    )
        if self.textFile2 is None or self.textFile2[0] == '':
            return
        try:
            lines = open(self.textFile2[0], 'r', encoding='UTF-8').read()
        except UnicodeDecodeError:
            lines = open(self.textFile2[0], 'r', encoding='cp949').read()
        self.textEditors[1].textEdit.setText(lines)

    # 텍스트 파일을 갱신하는 함수
    def update_text(self):
        if hasattr(self, 'textFile') and self.textFile[0] != '':
            texts = self.textEditors[0].textEdit.toPlainText()
            if 'filelist' in self.textFile[0]:
                utils.make_filelist(self.audioDir, texts.split('\n'), self.textFile[0])
            else:
                open(self.textFile[0], 'w', encoding='utf-8').write(texts)
        if hasattr(self, 'textFile2') and self.textFile2[0] != '':
            texts = self.textEditors[1].textEdit.toPlainText()
            if 'filelist' in self.textFile2[0]:
                utils.make_filelist(self.audioDir, texts.split('\n'), self.textFile2[0])
            else:
                open(self.textFile2[0], 'w', encoding='utf-8').write(texts)

    # UI 갱신 함수
    def refresh(self):
        # 텍스트 파일 저장
        self.update_text()
        # 테이블 갱신
        self.addAudioList(refresh=True)
        self.addTextList(refresh=True)

    # 오디오 자르는 함수
    def audio_split(self):
        self.AudioSplitWindow.exec()

    def audio_split_one(self):
        if not hasattr(self, 'audioDir') or len(self.selectedList) != 1:
            print('Select one')
            return
        selectedFile = self.playlist[self.selectedList[0]]
        print('*' * 50)
        print('selectedFile:', selectedFile)
        print('*' * 50)
        self.player.stop()
        # exec dialog
        self.AudioSplitOneWindow.set_file(selectedFile)
        self.AudioSplitOneWindow.exec()
        # update audio list
        self.addAudioList(refresh=True)

    # 오디오 붙이는 함수
    def audio_concat(self):
        if not hasattr(self, 'audioDir') or len(self.selectedList) == 1:
            print('Select multiple files')
            return
        self.player.stop()
        files = sorted([self.playlist[i] for i in self.selectedList])
        # exec dialog
        self.AudioConcatWindow.setup(files)
        self.AudioConcatWindow.exec()

    def audio_transform(self):
        if not hasattr(self, 'audioDir') or self.audioDir == '':
            return
        wavs = sorted(glob.glob(os.path.join(self.audioDir, '*.wav')))
        new_window = AudioTransformWindow(self, wavs)
        new_window.exec()

    # 시간 측정
    def time_measurement(self):
        if not hasattr(self, 'audioDir') or self.audioDir == '':
            return
        wavs = sorted(glob.glob(os.path.join(self.audioDir, '*.wav')))
        new_window = TimeMeasurementWindow(self, wavs)
        new_window.exec()

    # 파일 정렬
    def file_sort_dialog(self):
        if not hasattr(self, 'audioDir') or self.audioDir == '':
            return
        self.sort_dialog.show()

    def file_sort(self):
        # preprocess for nesting
        if os.path.exists(self.deleteDir):
            shutil.rmtree(self.deleteDir)
        wavs = sorted(glob.glob(os.path.join(self.audioDir, '*.wav')))
        for i, path in enumerate(wavs):
            # temp라는 이름으로 임시 변경
            os.rename(path, f'{self.audioDir}/temp_{i:04}.wav')
        time.sleep(0.1)
        wavs = sorted(glob.glob(os.path.join(self.audioDir, '*.wav')))
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
            # filelist가 input으로 들어왔을 때도 고려하기 때문에 다소 복잡하다.
            # It is somewhat complicated since filelist is also considered when it comes to into input
            lines = open(textFile, 'r', encoding='utf-8').readlines()
            files, texts = [], []
            for line in lines:
                splited = line.split('|')
                if len(splited) != 1:
                    files.append('|'.join(splited[:-1])+'|')
                else:
                    files.append('')
                texts.append(splited[-1])
            texts = ''.join(texts)
            lines_g2p = g2p(texts, descriptive=True, to_syl=True, use_dict=True).split('\n')
            new_lines = [file + line_g2p+'\n' for file, line_g2p in zip(files, lines_g2p)]
            f.write(''.join(new_lines))

    def make_filelist_dialog(self):
        if not hasattr(self, 'audioDir') or self.audioDir == '' or not hasattr(self, 'textFile') or self.textFile[0] == '':
            return
        self.filelist_dialog.show()

    # phoneme to jamo
    def make_filelist(self):
        _g2p, _jamo, _validation = [ckbx.isChecked() for ckbx in self.filelist_ckboxes]

        if _validation:
            dst_train = os.path.join(os.path.dirname(self.audioDir), 'train_' + self.filelist_name.text())
            dst_valid = os.path.join(os.path.dirname(self.audioDir), 'valid_' + self.filelist_name.text())
            dst = (dst_train, dst_valid)
        else:
            dst = os.path.join(os.path.dirname(self.audioDir), self.filelist_name.text())
        
        lines = open(self.textFile[0], 'r', encoding='UTF-8').readlines()
        lines = ''.join([line.split('|')[-1] for line in lines])
        if _g2p: lines = G2p()(lines, descriptive=True, to_syl=True, use_dict=True)
        if _jamo: lines = h2j(lines)
        lines = lines.split('\n')

        utils.make_filelist(self.audioDir, self.character.text(), lines, dst, _validation)
        self.filelist_dialog.close()

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
        self.selectedList = [_index]
        # UI 갱신
        # self.refresh()
        self.addAudioList(refresh=True)

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
        deletedFiles = sorted(glob.glob(os.path.join(self.deleteDir, '*.wav')), key=lambda x: int(os.path.basename(x).split('_')[0]))
        if not deletedFiles:
            return
        filename = os.path.basename(deletedFiles[-1])
        # 숫자 태그 제거
        originalFilename = filename[filename.find('_')+1:]
        originalPath = os.path.join(self.audioDir, originalFilename)
        # 복원
        shutil.move(deletedFiles[-1], originalPath)
        # UI 화면 갱신
        # self.refresh()
        new_index = bisect.bisect_left(self.playlist, originalPath)
        print(originalPath, new_index)
        self.addAudioList(refresh=True)
        self.updateMediaChanged(new_index)
        self.selectedList = [new_index]

    def btnClicked(self, id):
        if id==0:   #◀◀
            self.player.prev()
        elif id==1: #▶
            if self.table.rowCount()>0:
                self.player.play(startRow=self.selectedList[0])
        elif id==2: #■
            self.player.stop()
        elif id==3: #▶▶
            self.player.next()
        elif id==4:
            self.guideDialog.show()
 
    def tableDbClicked(self, e):
        self.player.play(startRow=self.selectedList[0])
 
    def volumeChanged(self):
        self.player.upateVolume(self.slider.value())
 
    def radClicked(self, id):
        self.playOption = id
        self.player.updatePlayMode(id)
 
    def paintEvent(self, e):
        self.table.setColumnWidth(0, int(self.table.width()*0.7))
        self.table.setColumnWidth(1, int(self.table.width()*0.2))
 
    def createPlaylist(self, files):
        self.playlist.clear()
        for file in files:
            self.playlist.append(file)
        self.player.createPlaylist(playlists=self.playlist, option=self.playOption)
 
    def updateMediaChanged(self, index):
        if index>=0:
            self.table.selectRow(index)
            # 배경 색을 흰색으로 하는 것은 기존의 노란색으로 하이라이트 되어 있던 것을 돌리는 행위입니다.
            self.updateTextEditor(self.textEditors, self.lastSelectedLine, 'White')
            # 배경을 노란색으로 하이라이트 처리
            self.updateTextEditor(self.textEditors, index, color='Yellow')
            self.lastSelectedLine = index

    def updateTextEditor(self, textEditors, index, color:str='Yellow') -> None:
        '''
        Editor의 커서를 현재 index 위치로 옮기고 배경색을 변경합니다.
        '''
        for textEditor in textEditors:
            textEdit = textEditor.textEdit
            cursor = QTextCursor(textEdit.document().findBlockByLineNumber(index))
            textEdit.setTextCursor(cursor)
            textEdit.moveCursor(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
            # 배경 색 변경
            textEdit.setTextBackgroundColor(QColor(color))
            textEdit.moveCursor(QTextCursor.MoveOperation.StartOfLine, QTextCursor.MoveMode.MoveAnchor)
            # 다음 인덱스로 넘어가기
            textEdit.moveCursor(QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.MoveAnchor)

    # text editor에 숫자 마킹하는 함수
    def insertCharacter(self, textEditors, index, character):
        if not (self.btnShowEditor1.isChecked() or self.btnShowEditor2.isChecked()):
            return
        for textEditor in textEditors:
            textEdit = textEditor.textEdit
            textBlock = textEdit.document().findBlockByLineNumber(index)
            text = textBlock.text()
            if text == '': continue
            if text[-1].isdigit():
                text = text[:-1] + str(character)
            else:
                text = text + str(character)
            cursor = QTextCursor(textBlock)
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()
            textEdit.setTextCursor(cursor)
            if index != 0:
                textEdit.insertPlainText('\n'+text)
            else:
                textEdit.insertPlainText(text)
            textEdit.moveCursor(QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.MoveAnchor)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = CWidget()
    sys.exit(app.exec_())
