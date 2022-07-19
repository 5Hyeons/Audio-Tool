
from jamo import h2j
from multiprocessing import Pool
from g2pk.g2pk import G2p
import yaml
import json

import torch
import re
import numpy as np
# from g2p_en import G2p
# from g2pk import G2p
# from jamo import h2j
# from pypinyin import pinyin, Style

from .utils.tools import to_device, synth_samples
from .text import text_to_sequence

from scipy.io import wavfile

from . import hifigan
from .model import FastSpeech2
from .dataset import CustomDataset
from .normalize.korean import normalize_upper
from torch.utils.data import DataLoader

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

PREPROCCESS_CONFIG_PATH = './FastSpeech2/config/AUDIOBOX_44k/preprocess.yaml'
# MODEL_CONFIG_PATH_OLD = './FastSpeech2/config/AUDIOBOX_44k/model_old.yaml'
MODEL_CONFIG_PATH = './FastSpeech2/config/AUDIOBOX_44k/model.yaml'
HIFI_CONFIG_PATH = './FastSpeech2/hifigan/config_v44k.json'


def get_model(model_path):

    # Read Config
    preprocess_config = yaml.load(
        open(PREPROCCESS_CONFIG_PATH, "r"), Loader=yaml.FullLoader
    )
    model_config = yaml.load(
        open(MODEL_CONFIG_PATH, "r"), Loader=yaml.FullLoader)

    model = FastSpeech2(preprocess_config, model_config).to(device)

    # ckpt = torch.load(model_path)
    # model.load_state_dict(ckpt["model"])
    #
    ckpt = torch.load(model_path)
    model_dict = model.state_dict()
    pretrained_w = {k: v for k, v in ckpt['model'].items()}

    word_emb_len = len(pretrained_w['encoder.src_word_emb.weight'])
    model_dict['encoder.src_word_emb.weight'][:word_emb_len,
                                              :] = pretrained_w['encoder.src_word_emb.weight']
    word_emb = model_dict['encoder.src_word_emb.weight']
    model_dict.update(pretrained_w)
    model_dict['encoder.src_word_emb.weight'] = word_emb
    model.load_state_dict(model_dict)
    #
    model.eval()
    model.requires_grad_ = False
    return model


def get_vocoder(model_path):

    with open(HIFI_CONFIG_PATH, "r") as f:
        config = json.load(f)
    config = hifigan.AttrDict(config)
    vocoder = hifigan.Generator(config)

    ckpt = torch.load(model_path)
    vocoder.load_state_dict(ckpt["generator"])
    vocoder.eval()
    vocoder.remove_weight_norm()
    vocoder.to(device)

    return vocoder


def expand(values, durations):
    out = list()
    for value, d in zip(values, durations):
        out += [value] * max(0, int(d))
    return np.array(out)


def synth_samples(predictions, vocoder, save_dir, ids):
    mel_predictions = predictions[1].transpose(1, 2)
    lengths = predictions[9] * 512
    wav_predictions = vocoder_infer(
        mel_predictions, vocoder, lengths=lengths
    )

    sampling_rate = 44100
    for id, wav in zip(ids, wav_predictions):
        save_path = save_dir + id + '.wav'
        wavfile.write(save_path, sampling_rate, wav)


def vocoder_infer(mels, vocoder, lengths=None):
    wavs = vocoder(mels).squeeze(1)

    wavs = (
        wavs.cpu().numpy()
        * 32767.0
    ).astype("int16")
    wavs = [wav for wav in wavs]

    for i in range(len(mels)):
        if lengths is not None:
            wavs[i] = wavs[i][: lengths[i]]
    return wavs


g2p = G2p()


def preprocess_korean(text):
    global g2p
    text = text.rstrip('\n').split(' ')
    text = [g2p(t) for t in text]
    phone = ' '.join(text)

    phone = h2j(phone)
    phone = list(filter(lambda p: p != ' ', phone))
    phone = '{' + '}{'.join(phone) + '}'
    phone = phone.replace('{.}', '{.}{sil}')
    phone = phone.replace('{/}', '{sp}')
    phone = phone.replace('}{', ' ')

    return phone


def inference(model, vocoder, texts, speaker, save_path, id=None):
    with Pool(16) as p:
        phones = p.map(preprocess_korean, texts)
    print(phones)
    dataset = CustomDataset(texts, phones, speaker, id)
    batchs = DataLoader(
        dataset,
        batch_size=16,
        collate_fn=dataset.collate_fn,
    )

    ids, raw_texts = [], []
    for batch in batchs:
        ids.extend(batch[0])
        raw_texts.extend(batch[1])
        phones = batch[3][0]

        def minihook(m, input):
            f_list = []
            for i, phone in enumerate(phones):
                if phone == 86:
                    f_list.append(i)
                input += tuple([f_list])
                return input

        handle_pre = model.variance_adaptor.register_forward_pre_hook(minihook)
        batch = to_device(batch, device)
        with torch.no_grad():
            # Forward
            output = model(
                *(batch[2:]),
            )
            handle_pre.remove()
            synth_samples(
                output,
                vocoder,
                save_path,
                batch[0]
            )

    assert len(ids) == len(raw_texts)

    return ids, raw_texts
