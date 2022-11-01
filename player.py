from PyQt5.QtMultimedia import QMediaPlaylist, QMediaContent, QMediaPlayer
from PyQt5.QtCore import Qt, QUrl
 
class CPlayer:
 
    def __init__(self, parent):
        # 윈도우 객체
        self.parent = parent
 
        self.player = QMediaPlayer()
        self.player.setPlaybackRate(1.0)
        self.player.currentMediaChanged.connect(self.mediaChanged)
         
        self.playlist = QMediaPlaylist()
 
    def play(self, startRow=0):
        self.stop()
        self.playlist.setCurrentIndex(startRow)
        self.player.play()
         
    def pause(self):
        self.player.pause()         
 
    def stop(self):
        self.player.stop()
 
    def prev(self):        
        self.playlist.previous()     
 
    def next(self):
        self.playlist.next()
 
    def createPlaylist(self, playlists, option=QMediaPlaylist.Sequential):        
        self.playlist.clear()      
 
        for path in playlists:
            url = QUrl.fromLocalFile(path)
            self.playlist.addMedia(QMediaContent(url))
 
        self.playlist.setPlaybackMode(option)
        self.player.setPlaylist(self.playlist)
 
    def updatePlayMode(self, option):
        self.playlist.setPlaybackMode(option)
 
    def upateVolume(self, vol):
        # self.player.setVolume(vol)
        vol = round(vol/50,2)
        print(vol)
        print(self.player.playbackRate())
        # self.player.setPlaybackRate(vol/50)
 
    def mediaChanged(self, e):
        self.parent.updateMediaChanged(self.playlist.currentIndex())       
 
    def getCurrentMedia(self):
        return self.playlist.currentMedia().canonicalUrl().toString()