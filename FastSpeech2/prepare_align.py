import argparse

import yaml

from preprocessor import ljspeech, aishell3, libritts, kdy, kss, ymh, lby


def main(config):
    if "LJSpeech" in config["dataset"]:
        ljspeech.prepare_align(config)
    if "AISHELL3" in config["dataset"]:
        aishell3.prepare_align(config)
    if "LibriTTS" in config["dataset"]:
        libritts.prepare_align(config)
    if "KDY" in config["dataset"]:
        kdy.prepare_align(config)
    if "kss" in config["dataset"]:
        kss.prepare_align(config)
    if "YMH" in config["dataset"]:
        ymh.prepare_align(config)
    if "LBY" in config["dataset"]:
        lby.prepare_align(config)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=str, help="path to preprocess.yaml")
    args = parser.parse_args()

    config = yaml.load(open(args.config, "r"), Loader=yaml.FullLoader)
    main(config)
