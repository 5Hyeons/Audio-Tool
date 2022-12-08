import os
import utils
import librosa
from scipy.io import wavfile
from pydub import AudioSegment

from PyQt5.QtWidgets import *
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot


class SplitAudioThread(QThread):
    poped = pyqtSignal(list)
    maxValue = pyqtSignal(int)
    curValue = pyqtSignal(int)
    def __init__(self):
        super().__init__()
    
    def setParameters(self, src, min_sil_len, silence_thresh):
        self.src = src
        self.min_sil_len = min_sil_len
        self.silence_thresh = silence_thresh

    def run(self):
        sound_file = AudioSegment.from_wav(self.src)
        keep_silence = 100

        if isinstance(keep_silence, bool):
            keep_silence = len(sound_file) if keep_silence else 0

        output_ranges = [
            [ start - keep_silence, end + keep_silence ]
            for (start,end)
                in self.detect_nonsilent(sound_file, self.min_sil_len, self.silence_thresh, seek_step=1)
        ]

        for range_i, range_ii in utils.pairwise(output_ranges):
            last_end = range_i[1]
            next_start = range_ii[0]
            if next_start < last_end:
                range_i[1] = (last_end+next_start)//2
                range_ii[0] = range_i[1]

        audio_chunks = [
            sound_file[ max(start,0) : min(end,len(sound_file)) ]
            for start,end in output_ranges
        ]

        del sound_file
        self.poped.emit(audio_chunks)

    def detect_silence(self, audio_segment, min_silence_len=1000, silence_thresh=-16, seek_step=1):
        """
        Returns a list of all silent sections [start, end] in milliseconds of audio_segment.
        Inverse of detect_nonsilent()

        audio_segment - the segment to find silence in
        min_silence_len - the minimum length for any silent section
        silence_thresh - the upper bound for how quiet is silent in dFBS
        seek_step - step size for interating over the segment in ms
        """
        seg_len = len(audio_segment)

        # you can't have a silent portion of a sound that is longer than the sound
        if seg_len < min_silence_len:
            return []

        # convert silence threshold to a float value (so we can compare it to rms)
        silence_thresh = utils.db_to_float(silence_thresh) * audio_segment.max_possible_amplitude

        # find silence and add start and end indicies to the to_cut list
        silence_starts = []

        # check successive (1 sec by default) chunk of sound for silence
        # try a chunk at every "seek step" (or every chunk for a seek step == 1)
        last_slice_start = seg_len - min_silence_len
        slice_starts = range(0, last_slice_start + 1, seek_step)
        self.maxValue.emit(last_slice_start+1)
        # guarantee last_slice_start is included in the range
        # to make sure the last portion of the audio is searched
        if last_slice_start % seek_step:
            slice_starts = utils.itertools.chain(slice_starts, [last_slice_start])

        for i in slice_starts:
            audio_slice = audio_segment[i:i + min_silence_len]
            if audio_slice.rms <= silence_thresh:
                silence_starts.append(i)
            self.curValue.emit(i+1)

        # short circuit when there is no silence
        if not silence_starts:
            return []

        # combine the silence we detected into ranges (start ms - end ms)
        silent_ranges = []

        prev_i = silence_starts.pop(0)
        current_range_start = prev_i

        for silence_start_i in silence_starts:
            continuous = (silence_start_i == prev_i + seek_step)

            # sometimes two small blips are enough for one particular slice to be
            # non-silent, despite the silence all running together. Just combine
            # the two overlapping silent ranges.
            silence_has_gap = silence_start_i > (prev_i + min_silence_len)

            if not continuous and silence_has_gap:
                silent_ranges.append([current_range_start,
                                    prev_i + min_silence_len])
                current_range_start = silence_start_i
            prev_i = silence_start_i

        silent_ranges.append([current_range_start,
                            prev_i + min_silence_len])

        return silent_ranges

    def detect_nonsilent(self, audio_segment, min_silence_len=1000, silence_thresh=-16, seek_step=1):
        """
        Returns a list of all nonsilent sections [start, end] in milliseconds of audio_segment.
        Inverse of detect_silent()

        audio_segment - the segment to find silence in
        min_silence_len - the minimum length for any silent section
        silence_thresh - the upper bound for how quiet is silent in dFBS
        seek_step - step size for interating over the segment in ms
        """
        silent_ranges = self.detect_silence(audio_segment, min_silence_len, silence_thresh, seek_step)
        len_seg = len(audio_segment)

        # if there is no silence, the whole thing is nonsilent
        if not silent_ranges:
            return [[0, len_seg]]

        # short circuit when the whole audio segment is silent
        if silent_ranges[0][0] == 0 and silent_ranges[0][1] == len_seg:
            return []

        prev_end_i = 0
        nonsilent_ranges = []
        for start_i, end_i in silent_ranges:
            nonsilent_ranges.append([prev_end_i, start_i])
            prev_end_i = end_i

        if end_i != len_seg:
            nonsilent_ranges.append([prev_end_i, len_seg])

        if nonsilent_ranges[0] == [0, 0]:
            nonsilent_ranges.pop(0)

        return nonsilent_ranges


# Time measurement thread
class AudioMeasurementThread(QThread):
    poped = pyqtSignal(int)
    def __init__(self, wavs, q):
        super().__init__()
        self.wavs = wavs
        self.q = q
        self.total_time = 0

    def run(self):
        while not self.q.empty():
            self.q.get()
        for i, wav in enumerate(self.wavs):
            if not self.q.empty():
                break
            sr, y = wavfile.read(wav)
            t = len(y)/sr
            self.total_time += t
            self.poped.emit(i+1)

class AudioTransformThread(QThread):
    '''오디오 파일을 44.1khz 모노타입으로 변환하는 쓰레드'''
    poped = pyqtSignal(int)
    def __init__(self, wavs, q):
        super().__init__()
        self.wavs = wavs
        self.q = q
        
    def run(self):
        while not self.q.empty():
            self.q.get()
        for i, wav in enumerate(self.wavs):
            if not self.q.empty():
                break
            y, sr = librosa.load(wav, sr=44100, mono=True)
            os.remove(wav)
            wavfile.write(wav, sr, y)
            self.poped.emit(i+1)