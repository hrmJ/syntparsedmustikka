import re
import sys
import csv
import insert_pair

if len(sys.argv)<4:
    sys.exit("Usage: {} <blogfile> <metadata file> <lang (ru/fi/.)> <db name> <metadata as csv (default yes)>".format(sys.argv[0]))

meta_as_csv = True

try:
    if sys.argv[5] in ('no','false','none'):
        meta_as_csv = False
except IndexError:
    meta_as_csv = True

splitpattern = re.compile(r"\d+\t![^\n]+\n\n?"*4 + r"\d+\t![^\n]+\n\n")

#Get all the individual posts
with open(sys.argv[1],"r") as f:
    conllinput = f.read()
posts = insert_pair.TrimList(re.split(splitpattern,conllinput))



#Get metadata

if meta_as_csv:
    texts = list()
    with open(sys.argv[2],'r') as inputdata:
        reader = csv.DictReader(inputdata)
        for line in reader:
            texts.append(line)
else:
    with open(sys.argv[2],"r") as f:
            metadata = f.read()
    texts = metadata.splitlines()


con = insert_pair.psycopg(sys.argv[4],'juho')


for idx, post in enumerate(posts):
    sl  = insert_pair.SourceText(table='{}_conll'.format(sys.argv[3]), inputfile=None, con=con, conllinput=post, blogmeta=texts[idx])
    sl.CollectSegments()
    sl.InsertToDb(con)
