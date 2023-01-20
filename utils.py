import os
import glob
import random
import itertools
from pydub import AudioSegment
from pydub.silence import split_on_silence

def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)

def db_to_float(db, using_amplitude=True):
    """
    Converts the input db to a float, which represents the equivalent
    ratio in power.
    """
    db = float(db)
    if using_amplitude:
        return 10 ** (db / 20)
    else:  # using power
        return 10 ** (db / 10)

def make_filelist(audioDir, defaultChar, lines, dst, validation=False):
    wavs = sorted(glob.glob(os.path.join(audioDir, '*.wav')))
    lines = list(lines) # copy lines
    random.seed(1997)
    idxs = range(min(len(wavs), len(lines)))
    valid_idxs = random.sample(idxs, min(10, len(idxs)//10))
    if isinstance(dst, tuple):
        t = open(dst[0], 'w', encoding='UTF8')
        v = open(dst[1], 'w', encoding='UTF8')
    else:
        t = open(dst, 'w', encoding='UTF8')

    for idx in idxs:
        filename = os.path.basename(wavs[idx])
        # insert characters
        char = lines[idx][-1]
        if not char.isdigit() or char == '0': # zero means that the character is setted by default
            char = defaultChar
        else:
            char = '0'+char if len(char)==1 else char # padding 0
            lines[idx] = lines[idx][:-1]
        new_line = f'{filename}|{char}|{lines[idx]}\n'
        new_line = new_line.replace('||', '|')
        if validation and idx in valid_idxs:
            v.write(new_line)
        else:
            t.write(new_line)
    if validation:
        v.close()
    t.close()
