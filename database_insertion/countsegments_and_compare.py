import sys
import re
from insert_pair import TrimList

class Skips:
    slist = [332,996,3498]

def tPrint(conll, txt, x):
    print(conll[x])
    print(txt[x])

def Comp(conll, txt, x, plus):
    x += plus
    print(conll[x])
    print(txt[x])
    return x

def FindDiff(conll, txt):
    if len(conll) != len(txt):
        for idx, seg in enumerate(conll):
            if idx not in Skips.slist:
                lnro = 0
                lines = seg.splitlines()
                try:
                    line = lines[lnro].split('\t')
                except IndexError:
                   tPrint(conll,txt,idx)
                   print('{}:{}'.format(conllword,txtword))
                   print(idx)
                   return idx

                token = line[1]
                finlet = r"[ÃabcdefghijklmnopqrstuvwxyzåäöАаБбВвГгДдЕеЁёЖжЗзИиЙйКкЛлМмНнОоПпРрСсТтУуФфХхЦцЧчШшЩщЪъЫыЬьЭэЮюЯя0-9]+"
                while not re.search(finlet, token, re.IGNORECASE):
                    lnro += 1
                    line = lines[lnro].split('\t')
                    try:
                        token = line[1]
                    except IndexError:
                        while not line[0]:
                            lnro += 1
                            line = lines[lnro].split('\t')
                        token = line[1]

                firstmatch = re.search(finlet,line[1],re.IGNORECASE)
                conllword = firstmatch.group(0)

                txtwords = txt[idx].split(' ')

                txtwords = ''.join(c if c.isalnum() else ' ' for c in txt[idx]).split()
                txtword = txtwords[0]

                if txtword != conllword:
                   tPrint(conll,txt,idx)
                   print('{}:{}'.format(conllword,txtword))
                   print(idx)
                   return idx
    else:
        print('sama määrä segmenttejä!')

with open(sys.argv[1],'r') as f:
    f1 = f.read()

with open(sys.argv[2],'r') as f:
    f2 = f.read()

splitpattern1 = re.compile(r"\d+\t![^\n]+\n\n?\d+\t![^\n]+\n\n?\d+\t![^\n]+\n\n?\d+\t![^\n]+\n\n")
splitpattern2 = re.compile(r"\n!{4}\n")

segs_conll = TrimList(re.split(splitpattern1,f1))
segs_txt = TrimList(re.split(splitpattern2,f2))

FindDiff(segs_conll, segs_txt)
