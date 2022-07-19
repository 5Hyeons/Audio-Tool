import os
import json

import torch
import numpy as np

from .. import hifigan
from ..model import FastSpeech2, ScheduledOptim

from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingWarmRestarts


def get_model(args, configs, device, train=False):
    (preprocess_config, model_config, train_config) = configs

    args_list = args._get_kwargs()
    model = FastSpeech2(preprocess_config, model_config).to(device)
    if args.restore_step == 0 and args.base_model is None and args.transfer_path is None:
        # Select latest ckpt
        ckpt_list = sorted([int(step.split('.')[0])
                           for step in os.listdir(train_config["path"]["ckpt_path"])])
        args.restore_step = ckpt_list[-1]
    if args.restore_step:
        ckpt_path = os.path.join(
            train_config["path"]["ckpt_path"],
            "{}.pth.tar".format(args.restore_step),
        )
        ckpt = torch.load(ckpt_path)
        model.load_state_dict(ckpt["model"])
    elif args.base_model is not None:
        ckpt = torch.load(args.base_model)
        model.load_state_dict(ckpt["model"])
    # Transfer learning encoder part by kss
    elif args.transfer_path:
        print('loading from kss for transfer learning ...')
        ckpt = torch.load(args.transfer_path)
        model_dict = model.state_dict()
        pretrained_encoder = {k: v for k,
                              v in ckpt['model'].items() if 'decoder' not in k}

        model_dict.update(pretrained_encoder)
        model.load_state_dict(model_dict)

    if train:
        scheduled_optim = ScheduledOptim(
            model, train_config, model_config, args.restore_step
        )
        if args.restore_step:
            scheduled_optim.load_state_dict(ckpt["optimizer"])
        model.train()
        return model, scheduled_optim

    model.eval()
    model.requires_grad_ = False
    return model


def get_param_num(model):
    num_param = sum(param.numel() for param in model.parameters())
    return num_param


def get_vocgan(ckpt_path, device, n_mel_channels=80, generator_ratio=[4, 4, 2, 2, 2, 2], n_residual_layers=4, mult=256, out_channels=1):

    checkpoint = torch.load(ckpt_path)
    model = Generator(n_mel_channels, n_residual_layers,
                      ratios=generator_ratio, mult=mult,
                      out_band=out_channels)

    model.load_state_dict(checkpoint['model_g'])
    model.to(device).eval()

    return model


def get_vocoder(config, device):
    name = config["vocoder"]["model"]
    speaker = config["vocoder"]["speaker"]
    model_path = config["vocoder"]["model_path"]

    if name == "MelGAN":
        if speaker == "LJSpeech":
            vocoder = torch.hub.load(
                "descriptinc/melgan-neurips", "load_melgan", "linda_johnson"
            )
        elif speaker == "universal":
            vocoder = torch.hub.load(
                "descriptinc/melgan-neurips", "load_melgan", "multi_speaker"
            )
        vocoder.mel2wav.eval()
        vocoder.mel2wav.to(device)
    elif name == "HiFi-GAN":
        with open("hifigan/config_v44k.json", "r") as f:
            config = json.load(f)
        config = hifigan.AttrDict(config)
        vocoder = hifigan.Generator(config)
        if speaker == "LJSpeech":
            ckpt = torch.load("hifigan/generator_LJSpeech.pth.tar")
        elif speaker == "universal":
            ckpt = torch.load("hifigan/generator_universal.pth.tar")
        else:
            ckpt = torch.load(model_path)
        vocoder.load_state_dict(ckpt["generator"])
        vocoder.eval()
        vocoder.remove_weight_norm()
        vocoder.to(device)
    elif name == "VocGAN":
        vocoder = get_vocgan(model_path, device)

    return vocoder


def vocoder_infer(mels, vocoder, model_config, preprocess_config, lengths=None):
    name = model_config["vocoder"]["model"]
    with torch.no_grad():
        if name == "MelGAN":
            wavs = vocoder.inverse(mels / np.log(10))
        elif name == "HiFi-GAN":
            wavs = vocoder(mels).squeeze(1)
        elif name == "VocGAN":
            max_wav_value = 32767.0
            hop_length = 256
            # wavs = vocoder.infer(mels)#.squeeze()
            if len(mels.shape) == 2:
                mels = mels.unsqueeze(0)

            audio = vocoder.infer(mels).squeeze()
            audio = max_wav_value * audio[:-(hop_length*10)]
            audio = audio.clamp(min=-max_wav_value, max=max_wav_value-1)
            audio = audio.unsqueeze(0)
            wavs = audio.short().cpu().detach().numpy()

    if name == "MalGAN" or name == "HiFi-GAN":
        wavs = (
            wavs.cpu().numpy()
            * preprocess_config["preprocessing"]["audio"]["max_wav_value"]
        ).astype("int16")
    wavs = [wav for wav in wavs]

    for i in range(len(mels)):
        if lengths is not None:
            wavs[i] = wavs[i][: lengths[i]]
    return wavs
