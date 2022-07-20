""" from https://github.com/keithito/tacotron """

'''
Cleaners are transformations that run over the input text at both training and eval time.

Cleaners can be selected by passing a comma-delimited list of cleaner names as the "cleaners"
hyperparameter. Some cleaners are English-specific. You'll typically want to use:
  1. "english_cleaners" for English text
  2. "transliteration_cleaners" for non-English text that can be transliterated to ASCII using
     the Unidecode library (https://pypi.python.org/pypi/Unidecode)
  3. "basic_cleaners" if you do not want to transliterate (in this case, you should also update
     the symbols in symbols.py to match your data).
'''

# from phonemizer import phonemize


# Regular expression matching whitespace:
# from g2pk.g2pk import G2p
from .g2p_custom import G2pC
from nltk.corpus import cmudict
from jamo import h2j
import re
from unidecode import unidecode

eng2kor = {
    'A': '에이',
    'B': '비',
    'C': '씨',
    'D': '디',
    'E': '이',
    'F': '에프',
    'G': '지',
    'H': '에이치',
    'I': '아이',
    'J': '제이',
    'K': '케이',
    'L': '엘',
    'M': '엠',
    'N': '엔',
    'O': '오',
    'P': '피',
    'Q': '큐',
    'R': '알',
    'S': '에스',
    'T': '티',
    'U': '유',
    'V': '브이',
    'W': '더블유',
    'X': '엑스',
    'Y': '와이',
    'Z': '지',
}


g2p = G2pC()

cmu = cmudict.dict()

def word_to_hangul(word):
    ret = ''
    for alpha in word:
        ret += eng2kor[alpha]
    return ret

def convert_to_hangul(text):
    def fn(m):
        word = m.group()
        if word.isupper():
            return word_to_hangul(word)
        if word.lower() not in cmu:
            return word_to_hangul(word.upper())
        return word
    text = re.sub(r'[A-Za-z]+', fn, text)
    return text


def korean(text, O):
    text = convert_to_hangul(text)
    phonemes = [g2p(t) for t in text.split()]
    phonemes = ' '.join(phonemes)
    phonemes = h2j(phonemes)
    if O == False:
        phonemes = phonemes.replace('ᄋ', '')
    return phonemes
