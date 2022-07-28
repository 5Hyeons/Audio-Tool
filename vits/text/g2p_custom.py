import re
from jamo import h2j
from g2pk.g2pk import G2p
from g2pk.special import jyeo, ye, consonant_ui, josa_ui, vowel_ui, jamo, rieulgiyeok, rieulbieub, verb_nieun, balb, palatalize, modifying_rieul
from g2pk.regular import link1, link2, link3, link4
from g2pk.utils import annotate, compose, group, gloss
from g2pk.english import convert_eng

class G2pC(G2p):
    def __init__(self):
        super().__init__()
        self.bound_nouns = "군데 권 개 그루 닢 대 두 마리 모 모금 뭇 발 발짝 방 번 벌 보루 살 수 술 시 쌈 움큼 정 짝 채 척 첩 축 켤레 톨 통 시간 가지 배"

    def __call__(self, string, descriptive=False, verbose=False, group_vowels=False, to_syl=True):
        # 1. idioms
        string = self.idioms(string, descriptive, verbose)

        # 2 English to Hangul
        string = convert_eng(string, self.cmu)

        # 3. annotate
        string = self.annotate(string, self.mecab)

        # 4. Spell out arabic numbers
        string = self.convert_num(string)

        # 5. decompose
        inp = h2j(string)

        # 6. special
        for func in (jyeo, ye, consonant_ui, josa_ui, vowel_ui, \
                     jamo, rieulgiyeok, rieulbieub, verb_nieun, \
                     balb, palatalize, modifying_rieul):
            inp = func(inp, descriptive, verbose)
        inp = re.sub("/[PJEB]", "", inp)

        # 7. regular table: batchim + onset
        for str1, str2, rule_ids in self.table:
            _inp = inp
            inp = re.sub(str1, str2, inp)

            if len(rule_ids)>0:
                rule = "\n".join(self.rule2text.get(rule_id, "") for rule_id in rule_ids)
            else:
                rule = ""
            gloss(verbose, inp, _inp, rule)

        # 8 link
        for func in (link1, link2, link3, link4):
            inp = func(inp, descriptive, verbose)

        # 9. postprocessing
        if group_vowels:
            inp = group(inp)

        if to_syl:
            inp = compose(inp)
        return inp

    def annotate(self, string, mecab):
        string = annotate(string, mecab)
        string = re.sub(r'\d+가지|\d+배|\d+시간', lambda x: x.group()+'/B', string)
        return string

    def process_num(self, num, sino=True):
        '''Process a string looking like arabic number.
        num: string. Consists of [0-9,]. e.g., 12,345
        sino: boolean. If True, sino-Korean numerals, i.e., 일, 이, .. are considered.
            Otherwise, pure Korean ones in their modifying forms such as 한, 두, ... are returned.
        >>> process_num("123,456,789", sino=True)
        일억이천삼백사십오만육천칠백팔십구
        >>> process_num("123,456,789", sino=False)
        일억이천삼백사십오만육천칠백여든아홉
        '''
        num = re.sub(",", "", num)

        if num == "0":
            return "영"
        if not sino and num == "20":
            return "스무"

        digits = "123456789"
        names = "일이삼사오육칠팔구"
        digit2name = {d: n for d, n in zip(digits, names)}

        modifiers = "한 두 세 네 다섯 여섯 일곱 여덟 아홉"
        decimals = "열 스물 서른 마흔 쉰 예순 일흔 여든 아흔"
        digit2mod = {d: mod for d, mod in zip(digits, modifiers.split())}
        digit2dec = {d: dec for d, dec in zip(digits, decimals.split())}

        spelledout = []
        for i, digit in enumerate(num):
            i = len(num) - i - 1
            if sino:
                if i == 0:
                    name = digit2name.get(digit, "")
                elif i == 1:
                    name = digit2name.get(digit, "") + "십"
                    name = name.replace("일십", "십")
            else:
                if i == 0:
                    name = digit2mod.get(digit, "")
                elif i == 1:
                    name = digit2dec.get(digit, "")
            if digit == '0':
                if i % 4 == 0:
                    last_three = spelledout[-min(3, len(spelledout)):]
                    if "".join(last_three) == "":
                        spelledout.append("")
                        continue
                else:
                    spelledout.append("")
                    continue
            if i == 2:
                name = digit2name.get(digit, "") + "백"
                name = name.replace("일백", "백")
            elif i == 3:
                name = digit2name.get(digit, "") + "천"
                name = name.replace("일천", "천")
            elif i == 4:
                name = digit2name.get(digit, "") + "만"
                name = name.replace("일만", "만")
            elif i == 5:
                name = digit2name.get(digit, "") + "십"
                name = name.replace("일십", "십")
            elif i == 6:
                name = digit2name.get(digit, "") + "백"
                name = name.replace("일백", "백")
            elif i == 7:
                name = digit2name.get(digit, "") + "천"
                name = name.replace("일천", "천")
            elif i == 8:
                name = digit2name.get(digit, "") + "억"
            elif i == 9:
                name = digit2name.get(digit, "") + "십"
            elif i == 10:
                name = digit2name.get(digit, "") + "백"
            elif i == 11:
                name = digit2name.get(digit, "") + "천"
            elif i == 12:
                name = digit2name.get(digit, "") + "조"
            elif i == 13:
                name = digit2name.get(digit, "") + "십"
            elif i == 14:
                name = digit2name.get(digit, "") + "백"
            elif i == 15:
                name = digit2name.get(digit, "") + "천"
            spelledout.append(name)

        return "".join(elem for elem in spelledout)

    def convert_num(self, string):
        '''Convert a annotated string such that arabic numerals inside are spelled out.
        >>> convert_num("우리 3시/B 10분/B에 만나자.")
        우리 세시/B 십분/B에 만나자.
        '''
        # Bound Nouns
        tokens = set(re.findall("([\d][\d,]*)( ?[ㄱ-힣]+)/B", string))
        for token in tokens:
            num, bn = token
            if bn in self.bound_nouns.split():
                spelledout = self.process_num(num, sino=False)
            else:
                spelledout = self.process_num(num, sino=True)
            string = string.replace(f"{num}{bn}/B", f"{spelledout}{bn}/B")

        # digit by digit for remaining digits
        digits = "0123456789"
        names = "영일이삼사오육칠팔구"
        for d, n in zip(digits, names):
            string = string.replace(d, n)

        return string