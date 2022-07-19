import argparse
import os

import torch
import yaml
import torch.nn as nn
import numpy as np
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter
from tqdm import tqdm

from utils.model import get_model, get_vocoder, get_param_num
from utils.tools import to_device, log, synth_one_sample, synth_samples_for_valid, synth_samples, make_textgrid
from model import FastSpeech2Loss
from dataset import Dataset

from evaluate import evaluate

from synthesize import preprocess_korean

from upload2notion import upload_files_to_notion

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def main(args, configs):
    print("Prepare training ...")

    preprocess_config, model_config, train_config = configs

    # Get dataset
    dataset = Dataset(
        "train.txt", preprocess_config, train_config, sort=True, drop_last=True
    )
    
    valid_path = preprocess_config['path']['validation_path']
    with open(valid_path, 'r') as f:
        valid_raw_texts = [line.strip() for line in f]
    valid_batch = []
    for raw_text in valid_raw_texts:
        texts, phone = preprocess_korean(raw_text.strip(), preprocess_config, False)
        texts = np.array([texts])
        text_lens = np.array([len(texts[0])])
        ids = 'asdf'
        speaker = np.array([0])
        valid_batch.append((ids, raw_text, speaker, texts, text_lens, max(text_lens), phone))


    batch_size = train_config["optimizer"]["batch_size"]
    group_size = 4  # Set this larger than 1 to enable sorting in Dataset
    assert batch_size * group_size < len(dataset)
    loader = DataLoader(
        dataset,
        batch_size=batch_size * group_size,
        shuffle=True,
        collate_fn=dataset.collate_fn,
        num_workers=8,
        pin_memory=True
    )

    # Prepare model
    model, optimizer = get_model(args, configs, device, train=True)
    model = nn.DataParallel(model)
    num_param = get_param_num(model)
    Loss = FastSpeech2Loss(preprocess_config, model_config).to(device)
    print("Number of FastSpeech2 Parameters:", num_param)

    # Load vocoder
    vocoder = get_vocoder(model_config, device)

    # Init logger
    for p in train_config["path"].values():
        os.makedirs(p, exist_ok=True)
    train_log_path = os.path.join(train_config["path"]["log_path"], "train")
    val_log_path = os.path.join(train_config["path"]["log_path"], "val")
    os.makedirs(train_log_path, exist_ok=True)
    os.makedirs(val_log_path, exist_ok=True)
    train_logger = SummaryWriter(train_log_path)

    # Training
    step = args.restore_step + 1
    epoch = 1
    grad_acc_step = train_config["optimizer"]["grad_acc_step"]
    grad_clip_thresh = train_config["optimizer"]["grad_clip_thresh"]
    total_step = train_config["step"]["total_step"]
    log_step = train_config["step"]["log_step"]
    save_step = train_config["step"]["save_step"]
    synth_step = train_config["step"]["synth_step"]
    val_step = train_config["step"]["val_step"]

    outer_bar = tqdm(total=total_step, desc="Training", position=0)
    outer_bar.n = args.restore_step
    outer_bar.update()

    while True:
        inner_bar = tqdm(total=len(loader), desc="Epoch {}".format(epoch), position=1)
        for batchs in loader:
            for batch in batchs:
                batch = to_device(batch, device)

                # Forward
                output = model(*(batch[2:]))

                # Cal Loss
                losses = Loss(batch, output)
                total_loss = losses[0]

                # Backward
                total_loss = total_loss / grad_acc_step
                total_loss.backward()
                if step % grad_acc_step == 0:
                    # Clipping gradients to avoid gradient explosion
                    nn.utils.clip_grad_norm_(model.parameters(), grad_clip_thresh)

                    # Update weights
                    optimizer.step_and_update_lr()
                    optimizer.zero_grad()

                if step % log_step == 0:
                    losses = [l.item() for l in losses]
                    message1 = "Step {}/{}, ".format(step, total_step)
                    message2 = "Total Loss: {:.4f}, Mel Loss: {:.4f}, Mel PostNet Loss: {:.4f}, Pitch Loss: {:.4f}, Energy Loss: {:.4f}, Duration Loss: {:.4f}".format(
                        *losses
                    )

                    with open(os.path.join(train_log_path, "log.txt"), "a") as f:
                        f.write(message1 + message2 + "\n")

                    outer_bar.write(message1 + message2)

                    log(train_logger, step, losses=losses)

                if step % synth_step == 0:
                    fig, wav_reconstruction, wav_prediction, tag = synth_one_sample(
                        batch,
                        output,
                        vocoder,
                        model_config,
                        preprocess_config,
                    )
                    
                    log(
                        train_logger,
                        fig=fig,
                        tag="Training/step_{}_{}_{}".format(step, tag, args.name),
                    )
                    sampling_rate = preprocess_config["preprocessing"]["audio"][
                        "sampling_rate"
                    ]
                    log(
                        train_logger,
                        audio=wav_reconstruction,
                        sampling_rate=sampling_rate,
                        tag="Training/step_{}_{}_{}_reconstructed".format(step, tag, args.name),
                    )
                    log(
                        train_logger,
                        audio=wav_prediction,
                        sampling_rate=sampling_rate,
                        tag="Training/step_{}_{}_{}_synthesized".format(step, tag, args.name),
                    )

                if step % val_step == 0:
                    path = os.path.join(train_config["path"]["result_path"], str(step))
                    if not os.path.exists(path):
                        os.makedirs(path)

                    model.eval()
                    durations = []
                    handle = model.module.variance_adaptor.register_forward_hook(lambda m, i, o: durations.append(o[4]))
                    # hook_handles.append(save_output)

                    for idx, batch in enumerate(valid_batch):
                        phones = batch[-1][1:-1].split()
                        batch = to_device(batch[:-1], device)
                        with torch.no_grad():
                            # Forward
                            output = model(*(batch[2:]))
                            make_textgrid(os.path.join(path, str(idx)), phones=phones, durations=durations[0][0])
                            durations.clear()
                            synth_samples(
                                batch,
                                output,
                                vocoder,
                                model_config,
                                preprocess_config,
                                path,
                                idx,
                                True                             
                            )
                    handle.remove()
                    sampling_rate = preprocess_config["preprocessing"]["audio"]["sampling_rate"]
                    vocoder_name = model_config['vocoder']['model_path']
                    upload_files_to_notion(path, args.name, step, 'AUDIOBOX', str(model_config["max_mel_len"]), sampling_rate, vocoder_name)
                    
                    handle.remove()
                    model.train()

                if step % save_step == 0:
                    torch.save(
                        {
                            "model": model.module.state_dict(),
                            "optimizer": optimizer._optimizer.state_dict(),
                        },
                        os.path.join(
                            train_config["path"]["ckpt_path"],
                            "{}.pth.tar".format(step),
                        ),
                    )

                if step == total_step:
                    quit()
                step += 1
                outer_bar.update(1)

            inner_bar.update(1)
        epoch += 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--restore_step", type=int, default=0)
    parser.add_argument('--base_model', type=str, default=None)
    parser.add_argument('--transfer_path', type=str, default=None)
    parser.add_argument('--name', type=str, default=None)
    parser.add_argument(
        "-p",
        "--preprocess_config",
        type=str,
        required=False,
        help="path to preprocess.yaml",
        default="config/AUDIOBOX_44k_sp/preprocess.yaml"
    )
    parser.add_argument(
        "-m", "--model_config", type=str, required=False, help="path to model.yaml", default="config/AUDIOBOX_44k_sp/model.yaml"
    )
    parser.add_argument(
        "-t", "--train_config", type=str, required=False, help="path to train.yaml", default="config/AUDIOBOX_44k_sp/train.yaml"
    )
    args = parser.parse_args()

    # Read Config
    preprocess_config = yaml.load(
        open(args.preprocess_config, "r"), Loader=yaml.FullLoader
    )
    model_config = yaml.load(open(args.model_config, "r"), Loader=yaml.FullLoader)
    train_config = yaml.load(open(args.train_config, "r"), Loader=yaml.FullLoader)
    configs = (preprocess_config, model_config, train_config)

    main(args, configs)
