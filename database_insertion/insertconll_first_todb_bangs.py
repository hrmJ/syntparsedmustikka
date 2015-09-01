#! /usr/bin/env python
import codecs
import csv
import sys
from dbmodule import psycopg
from progress.bar import Bar
import re

def GetLastValue(row):
    """Returns the first vacant index from the database"""
    try:
        if row[0][0] == None:
            return 0
        else:
            return row[0][0]
    except TypeError:
        return 0

#Get command line input:
try:
    conllinputfile = sys.argv[1]
    sl_dbname = sys.argv[2]
    tablename = sys.argv[3]
except IndexError:
    print('Usage: {} <path to conll formatted text file> <database name> <source language database table name>'.format(sys.argv[0]))
    sys.exit(0)

#================================================================================

#Connect to db
con = psycopg(sl_dbname,'juho')
#read the conll data
with open(conllinputfile, 'r') as f:
    conllinput = f.read()

# Split the file into aligned segments according to the !!!! -notation
splitpattern = re.compile(r"\d+\t![^\n]+\n\n\d+\t![^\n]+\n\n\d+\t![^\n]+\n\n\d+\t![^\n]+\n\n")
alignsegments = re.split(splitpattern,conllinput)
#Filter out empty align segments
alignsegments = list(filter(None, alignsegments)) 

#Get the current maximum indices:
sentence_id = GetLastValue(con.FetchQuery("SELECT max(sentence_id) FROM {}".format(tablename)))
align_id    = GetLastValue(con.FetchQuery("SELECT max(align_id) FROM {}".format(tablename)))
#Insert a new entry in the text_ids table
con.query("INSERT INTO text_ids (title) values(%s)", (input('Give a title for this text:\n'),))
text_id     = GetLastValue(con.FetchQuery("SELECT max(id) FROM text_ids"))

#Initialize variales for db insertion
rowlist = list()
bar = Bar('Preparing the data for insertion into the database', max=len(alignsegments))

#================================================================================
for segment in alignsegments:
    #Split each segment into lines (line=word with all the morphological and syntactic information)
    words = segment.splitlines()
    align_id    += 1
    sentence_id += 1
    for word in words:
        #read all the information about the word
        if word == '':
            #empty lines are sentence breaks
            sentence_id += 1
        else:
            columns = word.split('\t')
            #If this is a word with information, initialize a new row
            rowlist.append({'align_id'    : align_id,
                            'sentence_id' : sentence_id,
                            'text_id'     : text_id,
                            'tokenid'     : columns[0],
                            'token'       : columns[1],
                            'lemma'       : columns[2],
                            'pos'         : columns[4],
                            'feat'        : columns[5],
                            'head'        : columns[6],
                            'deprel'      : columns[7]})
    bar.next()
#================================================================================

bar.finish()
print('\nInserting to database, this might take a while...')
con.BatchInsert(tablename,rowlist)
print('Done. Inserted {} rows.'.format(con.cur.rowcount))
