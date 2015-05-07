#! /usr/bin/env python
#Import modules
import codecs
import csv
import sys
from collections import defaultdict
from lxml import etree
import string
import re
import logging
import time
#local modules
from dbmodule import mydatabase
from menus import Menu, multimenu, yesnomenu 
from search import Search, Match, Sentence, Word, ConstQuery, Db 
import itertools

try:
    dbname = sys.argv[1]
    table = sys.argv[2]
    sentence_id = sys.argv[3]
except:
    print('''Usage: {} 
    <db name>
    <table name>
    <sentence id>
    '''.format(sys.argv[0]))
    sys.exit(0)

#Connect to the database
con = mydatabase(dbname,'juho')
#Perform the query
sql_cols = "tokenid, token, lemma, pos, feat, head, deprel, align_id, id, sentence_id, text_id"
sqlq = "SELECT {0} FROM {1} WHERE sentence_id=%s order by id".format(sql_cols, table)


wordrows = con.dictquery(sqlq,(sentence_id,))

#Make this into a sentence object
ThisSentence = Sentence(sentence_id)

for wordrow in wordrows:
    ThisSentence.words[wordrow["tokenid"]] = Word(wordrow)

if "fi_" in table:
    ThisSentence.texvisualize('finnish')
else:
    ThisSentence.texvisualize('russian')
