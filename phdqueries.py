#! /usr/bin/env python
#Import modules
import codecs
import csv
import sys
from collections import defaultdict
from lxml import etree
import string
import re
#local modules
from dbmodule import mydatabase
from menus import Menu, multimenu, yesnomenu 
from search import Search, Match, Sentence, Word, ConstQuery, Db 
import itertools

class Csvlist:
    def __init__(self,csvpath):
        with open(csvpath, 'r') as f:
            self.aslist = list(csv.reader(f))

def joinidlist(idrows):
    idlist =  list(itertools.chain(*idrows))
    idlist = ','.join(map(str, idlist)) 
    return idlist

class FinnishTime:

    def __init__(self):
        #Restrict the number of align ids by means of sql
        #1. apply the conditions concerning the dependent word
        #1.1 condition about the lemma and the pos of the word
        allwords = Csvlist('/home/juho/phdmanuscript/data/parfin.taajuuslista.lemmatisoitu.vah3esiintymista.tarkistettu.csv')
        LemmaPosCondition = ''
        qwords = defaultdict(list)
        for row in allwords.aslist:
            if row[0] == 'y':
                if LemmaPosCondition:
                    LemmaPosCondition += " OR "
                LemmaPosCondition += "(lemma = '{}' AND pos = '{}')".format(row[1],row[2])
                #mark the pos as possible for this lemma
                qwords[row[1]].append(row[2])
        idq = "SELECT id FROM fi_conll WHERE ({}) ".format(LemmaPosCondition)
        #1.2 condition about the deprel of the word
        idq += "AND deprel in ('advmod','nommod','dobj','adpos')"
        #Get  the ids and use them in the next query
        idrows = Db.con.nondictquery(idq,())
        idlist = joinidlist(idrows)
        subq = "SELECT head, sentence_id FROM fi_conll WHERE id in ({})".format(idlist)

        ##2. apply the conditions concerning the head 
        FinnishTimeWordsSubQ = """ SELECT fi_conll.align_id  FROM ( {} ) as subq, fi_conll
                                    WHERE fi_conll.tokenid = subq.head
                                    AND fi_conll.sentence_id = subq.sentence_id 
                                    AND fi_conll.deprel in ('ROOT','advcl','cop','aux')""".format(subq)

        #idrows2 = Db.con.nondictquery(FinnishTimeWordsSubQ,())
        self.subq = FinnishTimeWordsSubQ
        self.qwords = qwords

