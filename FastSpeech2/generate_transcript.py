import os
import glob
from tqdm import tqdm

data_path = '/home/ubuntu/ChangNam/tts/LBY/wavs_with_labs'

# script_files = glob.glob(os.path.join(data_path, '**', '*.txt'), recursive=True)
script_files = glob.glob(os.path.join(data_path, '**', '*.lab'), recursive=True)

with open(os.path.join(data_path, 'transcript.txt'), 'w', encoding='utf-8') as f:
    for m in script_files:
        fn = m.split('/')[-1].split('.')[0]
        with open(m, encoding='utf-8') as scf:
            for line in tqdm(scf):
                # line = fn+'_'+line
                line = fn+'\t'+line+'\n'
                f.write(line)