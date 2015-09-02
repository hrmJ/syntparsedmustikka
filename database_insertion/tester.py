#! /usr/bin/env python
import csv
import sys
import re
from dbmodule import psycopg
from insertconll_first_todb_bangs import GetLastValue
from progress.bar import Bar

class MissingTextError(Exception):
    pass

class AlignMismatch(Exception):
    pass

with open('/home/juho/corpora2/syntparrus2/ru_conll/pr_zavsenadoplatit.tmx_ru.prepared.conll', 'r') as f:
    ru_input = f.read()
with open('/home/juho/corpora2/syntparrus2/fi_conll/pr_zavsenadoplatit.tmx_fi.prepared.conll', 'r') as f:
    fi_input = f.read()

# Split the translation file into aligned segments according to the !!!! -notation
splitpattern = re.compile(r"\d+\t![^\n]+\n\n?\d+\t![^\n]+\n\n?\d+\t![^\n]+\n\n?\d+\t![^\n]+\n\n")
ru_segments_a = re.split(splitpattern,ru_input)
ru_segments = list(filter(None, ru_segments_a)) 
fi_segments_a = re.split(splitpattern,fi_input)
fi_segments = list(filter(None, fi_segments_a)) 

ru1 = ru_segments_a[0:]
fi1 = fi_segments_a[0:]

for idx, seg in enumerate(ru1):
    rs = ru1[idx]
    fs = fi1[idx]
    if fs == '' and rs != '':
        import ipdb; ipdb.set_trace()
        pass

