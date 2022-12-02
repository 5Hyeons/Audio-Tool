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

def make_filelist(audioDir, lines, dst, validation=False):
    wavs = sorted(glob.glob(os.path.join(audioDir, '*.wav')))
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
        new_line = f'{filename}|{lines[idx]}\n'
        if validation and idx in valid_idxs:
            v.write(new_line)
        else:
            t.write(new_line)
    if validation:
        v.close()
    t.close()
