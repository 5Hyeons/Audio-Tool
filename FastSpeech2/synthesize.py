import re
import argparse
from string import punctuation
import os

import torch
import yaml
import numpy as np
from torch.utils.data import DataLoader
# from g2p_en import G2p
from g2pk import G2p
from jamo import h2j
# from pypinyin import pinyin, Style

from FastSpeech2.utils.model import get_model, get_vocoder
from .utils.tools import to_device, synth_samples
from .dataset import TextDataset
from .text import text_to_sequence

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def read_lexicon(lex_path):
    lexicon = {}
    with open(lex_path) as f:
        for line in f:
            temp = re.split(r"\s+", line.strip("\n"))
            word = temp[0]
            phones = temp[1:]
            if word.lower() not in lexicon:
                lexicon[word.lower()] = phones
    return lexicon


def preprocess_english(text, preprocess_config):
    text = text.rstrip(punctuation)
    lexicon = read_lexicon(preprocess_config["path"]["lexicon_path"])

    g2p = G2p()
    phones = []
    words = re.split(r"([,;.\-\?\!\s+])", text)
    for w in words:
        if w.lower() in lexicon:
            phones += lexicon[w.lower()]
        else:
            phones += list(filter(lambda p: p != " ", g2p(w)))
    phones = "{" + "}{".join(phones) + "}"
    phones = re.sub(r"\{[^\w\s]?\}", "{sp}", phones)
    phones = phones.replace("}{", " ")

    print("Raw Text Sequence: {}".format(text))
    print("Phoneme Sequence: {}".format(phones))
    sequence = np.array(
        text_to_sequence(
            phones, preprocess_config["preprocessing"]["text"]["text_cleaners"]
        )
    )

    return np.array(sequence)


def preprocess_mandarin(text, preprocess_config):
    pass
    """
    lexicon = read_lexicon(preprocess_config["path"]["lexicon_path"])

    phones = []
    pinyins = [
        p[0]
        for p in pinyin(
            text, style=Style.TONE3, strict=False, neutral_tone_with_five=True
        )
    ]
    for p in pinyins:
        if p in lexicon:
            phones += lexicon[p]
        else:
            phones.append("sp")

    phones = "{" + " ".join(phones) + "}"
    print("Raw Text Sequence: {}".format(text))
    print("Phoneme Sequence: {}".format(phones))
    sequence = np.array(
        text_to_sequence(
            phones, preprocess_config["preprocessing"]["text"]["text_cleaners"]
        )
    )

    return np.array(sequence)
    """
def preprocess_korean(text, preprocess_config, pr):
    # _punct = r""""#$%&'()*+,-/:;<=>@[\]^_`{|}~"""
    # punctuation = r"""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~""" # from string.py
    # text = text.rstrip(punctuation).split(' ')
    text = text.rstrip().split(' ')

    g2p=G2p()
    text = [g2p(t) for t in text]
    phone = ' '.join(text)

    if pr: print('after g2p: ',phone)
    phone = h2j(phone)
    if pr: print('after h2j: ',phone)
    phone = list(filter(lambda p: p != ' ', phone))
    phone = '{' + '}{'.join(phone) + '}'
    if pr: print('phone: ',phone)
    phone = phone.replace('{.}', '{.}{sil}')
    phone = phone.replace('{/}', '{sp}')    
    if pr: print('after re.sub: ',phone)
    phone = phone.replace('}{', ' ')

    if pr: print('|' + phone + '|')
    sequence = np.array(text_to_sequence(phone, preprocess_config["preprocessing"]["text"]["text_cleaners"]))
    return np.array(sequence), phone

def preprocess_korean_old(text, preprocess_config, pr):
    # _punct = r""""#$%&'()*+,-/:;<=>@[\]^_`{|}~"""
    # punctuation = r"""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~""" # from string.py
    # text = text.rstrip(punctuation).split(' ')
    text = text.rstrip().split(' ')

    g2p=G2p()
    text = [g2p(t) for t in text]
    phone = ' '.join(text)

    if pr: print('after g2p: ',phone)
    phone = h2j(phone)
    if pr: print('after h2j: ',phone)
    phone = list(filter(lambda p: p != ' ', phone))
    phone = '{' + '}{'.join(phone) + '}'
    if pr: print('phone: ',phone)
    phone = phone.replace('{.}', '{f}{sp}{sp}{sp}')
    phone = phone.replace('{?}', '{q}{sp}')
    phone = phone.replace('{,}', '{c}{sp}')
    phone = phone.replace('{!}', '{e}{sp}')    
    phone = phone.replace('{/}', '{sp}')    
    phone = phone.replace('{\'}', '{x}')
    phone = re.sub(r'\{[^\w\s]?\}', '{sp}', phone)
    if pr: print('after re.sub: ',phone)
    phone = phone.replace('}{', ' ')

    if pr: print('|' + phone + '|')
    sequence = np.array(text_to_sequence(phone, preprocess_config["preprocessing"]["text"]["text_cleaners"]))
    return np.array(sequence), phone

def synthesize(model, step, configs, vocoder, batchs, control_values, save_mels):
    preprocess_config, model_config, train_config = configs
    pitch_control, energy_control, duration_control = control_values

    for idx, batch in enumerate(batchs):
        batch = to_device(batch, device)
        with torch.no_grad():
            # Forward
            output = model(
                *(batch[2:]),
                p_control=pitch_control,
                e_control=energy_control,
                d_control=duration_control
            )
            synth_samples(
                batch,
                output,
                vocoder,
                model_config,
                preprocess_config,
                train_config["path"]["result_path"],
                idx,
                save_mels
            )

def t_or_f(arg):
    ua = str(arg).upper()
    if 'TRUE'.startswith(ua):
       return True
    elif 'FALSE'.startswith(ua):
       return False
    else:
       pass  #error condition maybe?

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--restore_step", type=int)
    parser.add_argument("--base_model", type=str, help="path to FastSpeech2 model")
    parser.add_argument("--vocoder", type=str )
    parser.add_argument("--vocoder_model", type=str, help="path to vocoder model")
    parser.add_argument("--save_mels", type=t_or_f, default=True, help='Whether to save mels or not')
    parser.add_argument("--print", type=t_or_f, default=True, help='Whether to print out the preprocessing results')
    parser.add_argument(
        "--mode",
        type=str,
        choices=["batch", "single"],
        required=True,
        help="Synthesize a whole dataset or a single sentence",
    )
    parser.add_argument(
        "--source",
        type=str,
        default=None,
        help="path to a source file with format like train.txt and val.txt for batch mode, or with text sequence for single mode",
    )
    parser.add_argument(
        "--text",
        type=str,
        default=None,
        help="raw text to synthesize, for single-sentence mode only",
    )
    parser.add_argument(
        "--stored_path",
        type=str,
        default=None,
        help="path of wav and png files synthesized",
    )
    parser.add_argument(
        "--speaker_id",
        type=int,
        default=0,
        help="speaker ID for multi-speaker synthesis, for single-sentence mode only",
    )
    parser.add_argument(
        "-p",
        "--preprocess_config",
        type=str,
        required=True,
        help="path to preprocess.yaml",
    )
    parser.add_argument(
        "-m", "--model_config", type=str, required=True, help="path to model.yaml"
    )
    parser.add_argument(
        "-t", "--train_config", type=str, required=True, help="path to train.yaml"
    )
    parser.add_argument(
        "--pitch_control",
        type=float,
        default=1.0,
        help="control the pitch of the whole utterance, larger value for higher pitch",
    )
    parser.add_argument(
        "--energy_control",
        type=float,
        default=1.0,
        help="control the energy of the whole utterance, larger value for larger volume",
    )
    parser.add_argument(
        "--duration_control",
        type=float,
        default=1.0,
        help="control the speed of the whole utterance, larger value for slower speaking rate",
    )
    args = parser.parse_args()

    if args.restore_step is None and args.base_model is None:
        assert args.restore_step is not None and args.base_model is not None, "At least one must have a value." 
    if args.restore_step is not None and args.base_model is not None:
        assert args.restore_step is None and args.base_model is None, "Cannot input restore_step and base_model at the same time"
    # assert args.vocoder_model is not None

    # Check source texts
    if args.mode == "batch":
        assert args.source is not None and args.text is None
    if args.mode == "single":
        if args.source is not None and args.text is None:
            with open(args.source, encoding='utf-8') as f:
                sentences = [line.strip() for line in f]
        elif args.source is None and args.text is not None:
            sentences = [args.text]
    
    
    # Read Config
    preprocess_config = yaml.load(
        open(args.preprocess_config, "r"), Loader=yaml.FullLoader
    )
    model_config = yaml.load(open(args.model_config, "r"), Loader=yaml.FullLoader)
    if args.vocoder is not None:
        model_config["vocoder"]["model"] = args.vocoder
    if args.vocoder_model is not None:
        model_config["vocoder"]["model_path"] = args.vocoder_model

    print(model_config["vocoder"]["model"])
    train_config = yaml.load(open(args.train_config, "r"), Loader=yaml.FullLoader)
    if args.stored_path is not None:
        os.makedirs(args.stored_path, exist_ok=True)
        train_config["path"]["result_path"] = args.stored_path
        
    configs = (preprocess_config, model_config, train_config)

    # Get model
    model = get_model(args, configs, device, train=False)

    # Load vocoder
    vocoder = get_vocoder(model_config, device)

    batchs = []
    # Preprocess texts
    if args.mode == "batch":
        # Get dataset
        dataset = TextDataset(args.source, preprocess_config)
        batchs = DataLoader(
            dataset,
            batch_size=8,
            collate_fn=dataset.collate_fn,
        )
    if args.mode == "single":
        for i, s in enumerate(sentences):
            args.text = s.strip()
            ids = raw_texts = [args.text[:100]]
            speakers = np.array([args.speaker_id])
            if preprocess_config["preprocessing"]["text"]["language"] == "en":
                texts = np.array([preprocess_english(args.text, preprocess_config)])
            elif preprocess_config["preprocessing"]["text"]["language"] == "zh":
                texts = np.array([preprocess_mandarin(args.text, preprocess_config)])
            elif preprocess_config["preprocessing"]["text"]["language"] == "ko":
                texts = np.array([preprocess_korean(args.text, preprocess_config, args.print)])
            text_lens = np.array([len(texts[0])])
            batchs.append((ids, raw_texts, speakers, texts, text_lens, max(text_lens)))

    control_values = args.pitch_control, args.energy_control, args.duration_control
    
    synthesize(model, args.restore_step, configs, vocoder, batchs, control_values, args.save_mels)
