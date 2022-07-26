import os
import json
import math
from random import shuffle
import torch
import uuid
from torch import nn
from torch.nn import functional as F
from torch.utils.data import DataLoader

from . import utils
from . import commons

from .data_utils import CustomLoader, CustomCollate
from .models import SynthesizerTrn
from .text.symbols import symbols
from .text import text_to_sequence, _id_to_symbol

from scipy.io import wavfile
from multiprocessing import Pool


device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# CONFIG_PATH = './vits/configs/tokyom.json'
# hps = utils.get_hparams_from_file(CONFIG_PATH)


# def get_text(text):
#     text_norm = text_to_sequence(text, hps.data.text_cleaners)
#     if hps.data.add_blank:
#         text_norm = commons.intersperse(text_norm, 0)
#     text_norm = torch.LongTensor(text_norm)
#     return text_norm


# def get_model_vits(model_path, config_path=CONFIG_PATH):
def get_model_vits(model_path):
    # Read Config
    global hps
    config_path = os.path.join(os.path.dirname(model_path), 'config.json')
    hps = utils.get_hparams_from_file(config_path)
    net_g = SynthesizerTrn(
        len(symbols),
        hps.data.filter_length // 2 + 1,
        hps.train.segment_size // hps.data.hop_length,
        n_speakers=hps.data.n_speakers,
        **hps.model).cuda()
    _ = net_g.eval()

    _ = utils.load_checkpoint(utils.latest_checkpoint_path(model_path, '*.pth'), net_g, None)

    return net_g


def synth_samples(loader, model, save_paths, sid):
    mean, var, dur = utils.set_parameters(sid)    
    i = 0
    with torch.no_grad():
        for x, x_lengths, speakers, brackets in loader:
            x, x_lengths = x.cuda(), x_lengths.cuda()
            speakers = speakers.cuda()

            audios, attn, mask, w_ceil, * \
                _ = model.infer(x, x_lengths, sid=speakers, noise_scale=var,
                                noise_scale_w=0.3, length_scale=dur, brackets=brackets, mean=mean)
            audio_lenths = mask.sum([1, 2]).long() * hps.data.hop_length
            for audio, length in zip(audios, audio_lenths):
                length = length.data.cpu().long().numpy()
                audio = audio[0].data.cpu().float().numpy()[:length]

                wavfile.write(save_paths[i], hps.data.sampling_rate, audio)
                i += 1
            del attn, w_ceil
            torch.cuda.empty_cache()
    return save_paths


def inference(model, texts, speaker, save_dir, id=None, O=True):
    ids, save_paths = [], []
    if id is None:
        for i in range(len(texts)):
            new_id = uuid.uuid4().hex[:16]
            ids.append(new_id)
            save_paths.append(os.path.join(save_dir, f'{new_id}.wav'))
    elif id is not None:
        ids.append(id)

        save_paths.append(os.path.join(save_dir, f'{id}.wav'))

    dataset = CustomLoader(texts, speaker, O=O)
    collate_fn = CustomCollate()
    loader = DataLoader(dataset, num_workers=8, shuffle=False,
                        batch_size=8, pin_memory=True,
                        drop_last=False, collate_fn=collate_fn, prefetch_factor=2)

    synth_samples(loader, model, save_paths)

    return ids, texts
