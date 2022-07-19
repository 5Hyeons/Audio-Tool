from numpy.lib.utils import source
from utils import *
from tqdm import tqdm
from glob import glob
import re
import os 
import unicodedata as ud
class KDY():
	def __init__(self, dataset_name, source_dataset_path, source_folder_list, savepath, savepath_wavs, metadata_savepath, grapheme_dictionary_savepath, phoneme_dictionary_savepath, num_threads):
		self.dataset_name = dataset_name
		self.source_dataset_path = source_dataset_path
		self.source_folder_list = source_folder_list
		self.savepath = savepath
		self.savepath_wavs = savepath_wavs
		self.metadata_savepath = metadata_savepath
		self.grapheme_dictionary_savepath = grapheme_dictionary_savepath
		self.phoneme_dictionary_savepath = phoneme_dictionary_savepath
		self.num_threads = num_threads


	def job(self, filepath):
		pass

	def prepare_mfa_training(self, metadata='metadata.csv'):
		patt = re.compile("[^\t]+")
		folder_list = sorted((os.path.join(self.source_dataset_path, o) for o in self.source_folder_list))
		print(folder_list)
		for fn_dir in folder_list:			
			fn = os.path.split(fn_dir)[-1]
			print(fn)
			lines = read_meta(get_path(fn_dir,'txt', metadata))
			print(fn, len(lines), '개')

			copy_file(source_file=" -r {}".format(get_path(fn_dir, "wav/*.wav")), dest_file="{}/".format(self.savepath))
			
			for f in glob(os.path.join(self.savepath, '?????.wav')):
				os.rename(f, os.path.join(self.savepath, '{}_{}'.format(fn, os.path.basename(f))))

			for line in tqdm(lines):
				wav_name, transcript = patt.findall(line)
				transcript = re.sub(r'[\n\t]*', '', transcript)
				if not check_character(transcript):
					print(fn, wav_name, '잘못된 문자 있음')
					continue
				lab_name = '{}_{}.lab'.format(fn, wav_name) 
				lab_path = get_path(self.savepath, lab_name)
				write_file(lab_path, transcript)

		print("\n[LOG] create phoneme dictionary...")
		grapheme_dictionary, phoneme_dictionary = create_grapheme_phoneme_dictionary(self.savepath)	

		print("\n[LOG] write grapheme and phoneme dictionary and metadata...")	
		write_dictionary(savepath=self.grapheme_dictionary_savepath, dictionary=grapheme_dictionary)
		write_dictionary(savepath=self.phoneme_dictionary_savepath, dictionary=phoneme_dictionary)

		print("[LOG] done!\n")

class AIPARK():

	def __init__(self, source_dataset_path, savepath, savepath_wavs, metadata_savepath, grapheme_dictionary_savepath, phoneme_dictionary_savepath, num_threads):
		self.source_dataset_path = source_dataset_path
		self.savepath = savepath
		self.savepath_wavs = savepath_wavs
		self.metadata_savepath = metadata_savepath
		self.grapheme_dictionary_savepath = grapheme_dictionary_savepath
		self.phoneme_dictionary_savepath = phoneme_dictionary_savepath
		self.num_threads = num_threads


	def job(self, filepath):
		pass

	def copy_files(self, metadata='metadata.csv', src="*/wav/*.wav"):
		# file 옮기기 
		copy_file(source_file="{}".format(get_path(self.source_dataset_path, src)), dest_file="{}/".format(self.savepath))
		copy_file(source_file="{}".format(get_path(self.source_dataset_path, src)), dest_file="{}/".format(self.savepath_wavs))
		copy_file(source_file=get_path(self.source_dataset_path, metadata), dest_file="{}".format(self.metadata_savepath))

	def merge_metafile(self, files, result_filename='result.txt'):
		res = pd.DataFrame(columns=(0, 1))
		for f in files:
			filename, file_extension = os.path.splitext(f)
			if file_extension == '.xlsx':
				dfs = pd.read_excel(f, sheet_name='Sheet1', usecols=(0, 1), header=None)
				dfs = dfs.dropna(axis=0)
				res = res.append(dfs)
		print(len(res), '문장')
		res.to_csv(result_filename, sep='\t', index=False)

	def make_labs_by_metafile(self, metadata='result.txt', tgt_dir='', remove_special_characters=True):
		os.makedirs(tgt_dir, exist_ok=True)
		patt = re.compile("[^\t]+")

		if remove_special_characters:
			hangul = re.compile('[^ ㄱ-ㅣ가-힣]+') # 한글과 띄어쓰기를 제외한 모든 글자
		lines = read_meta(get_path(self.source_dataset_path, metadata))

		# lab 파일 만들기 
		for line in tqdm(lines):
			
			wav_name, transcript = patt.findall(line)
			lab_name = wav_name + '.lab'
			lab_path = os.path.join(tgt_dir, lab_name)
			if remove_special_characters:
				transcript = hangul.sub('', transcript)
			print(transcript)
			print(lab_path)
			write_file(lab_path, transcript)

	def create_dicts(self, labs_path, depth=0, remove_special_characters=False, grapheme_dictionary_savepath='', phoneme_dictionary_savepath=''):
		# create phoneme dictionary 
		print("create grapheme dictionary and phoneme dictionary...")
		print(grapheme_dictionary_savepath, phoneme_dictionary_savepath)
		grapheme_dictionary, phoneme_dictionary = create_grapheme_phoneme_dictionary(labs_path, depth=depth, remove_special_characters=remove_special_characters)
		write_dictionary(savepath=grapheme_dictionary_savepath, dictionary=grapheme_dictionary)
		write_dictionary(savepath=phoneme_dictionary_savepath, dictionary=phoneme_dictionary)

	def prepare_mfa_training(self, metadata='metadata.csv'):
		print('')