import sys
import torch
from audio.stft import STFT
from utils.model import vocoder_infer

class Denoiser(torch.nn.Module):
    """ Removes model bias from audio produced with hifigan """

    def __init__(self, hifigan, model_config, preprocess_config, filter_length=1024, n_overlap=4,
                 win_length=1024, mode='zeros'):
        super(Denoiser, self).__init__()
        self.n_mel_channels = preprocess_config['mel']['n_mel_channels']
        self.filter_length = preprocess_config['preprocessing']['stft']['filter_length']
        self.hop_length = preprocess_config['preprocessing']['stft']['hop_length']
        self.win_length = preprocess_config['preprocessing']['stft']['win_length']
        self.max_seq_len = model_config['max_seq_len']
        self.stft = STFT(filter_length=self.filter_length,
                         hop_length=self.hop_length,
                         win_length=self.win_length).cuda()

        if mode == 'zeros':
            mel_input = torch.zeros(
                (1, self.n_mel_channels, self.max_seq_len),
                dtype=hifigan.conv_pre.weight.dtype,
                device=hifigan.conv_pre.weight.device)
        elif mode == 'normal':
            mel_input = torch.randn(
                (1, self.n_mel_channels, self.max_seq_len),
                dtype=hifigan.conv_pre.weight.dtype,
                device=hifigan.conv_pre.weight.device)
        else:
            raise Exception("Mode {} if not supported".format(mode))

        with torch.no_grad():
            # lengths = self.max_seq_len * preprocess_config['preprocessing']['stft']['hop_length']
            bias_audio = vocoder_infer(mel_input, hifigan, model_config, preprocess_config)
            bias_spec, _ = self.stft.transform(bias_audio)

        self.register_buffer('bias_spec', bias_spec[:, :, 0][:, :, None])

    def forward(self, audio, strength=0.1):
        audio_spec, audio_angles = self.stft.transform(audio.cuda().float())
        audio_spec_denoised = audio_spec - self.bias_spec * strength
        audio_spec_denoised = torch.clamp(audio_spec_denoised, 0.0)
        audio_denoised = self.stft.inverse(audio_spec_denoised, audio_angles)
        return audio_denoised