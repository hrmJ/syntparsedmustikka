import re
import sys
import csv
import insert_pair

if len(sys.argv)<2:
    sys.exit("Usage: {} <blogfile> <metadata file>".format(sys.argv[0]))


splitpattern = re.compile(r"\d+\t![^\n]+\n\n?"*9 + r"\d+\t![^\n]+\n\n")

#Get all the individual posts
with open(sys.argv[1],"r") as f:
    conllinput = f.read()
posts = insert_pair.TrimList(re.split(splitpattern,conllinput))

with open(sys.argv[2],"r") as f:
    metadata = f.read()

#Get metadata
texts = list()
with open(sys.argv[2],'r') as inputdata:
    reader = csv.DictReader(inputdata)
    for line in reader:
        texts.append(line)

con = insert_pair.psycopg('tbcorpfi','juho')


for idx, post in enumerate(posts):
    sl  = insert_pair.SourceText(table='ru_conll', inputfile=None, con=con, conllinput=post, blogmeta=texts[idx])
    sl.CollectSegments()
    sl.InsertToDb(con)
