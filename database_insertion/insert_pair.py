#! /usr/bin/env python
import sys
import os
from dbmodule import psycopg
from progress.bar import Bar
import re
from insert_translation import MissingTextError, AlignMismatch

class ArgumentError(Exception):
    pass

class TextPair():
    """A text on its way to the database"""
    splitpattern = re.compile(r"\d+\t![^\n]+\n\n?\d+\t![^\n]+\n\n?\d+\t![^\n]+\n\n?\d+\t![^\n]+\n\n")

    def __init__(self, table, inputfile):
        self.table = table
        #Read the data from the file and save it in a list called 'alignsegments'
        self.inputfile = inputfile
        with open(inputfile, 'r') as f:
            conllinput = f.read()
        self.alignsegments = TrimList(re.split(TextPair.splitpattern,conllinput))

    def InsertToDb(self, con):
        """Make the actual connection to tb"""
        print('\nInserting to table {}, this might take a while...'.format(self.table))
        con.BatchInsert(self.table,self.rowlist)
        print('Done. Inserted {} rows.'.format(con.cur.rowcount))

    def CollectSegments(self):
        self.rowlist = list()
        self.bar = Bar('Preparing the data for insertion into the database', max=len(self.alignsegments))
        self.LoopThroughSegments()
        self.bar.finish()


    def ProcessWordsOfSegment(self, tokenlines):
        tokenlines = TrimList(tokenlines)
        for word in tokenlines:
            #read all the information about the word
            if word == '':
                #empty lines are sentence breaks
                self.sentence_id += 1
            else:
                columns = word.split('\t')
                self.rowlist.append(AddRow(columns, self.current_align_id, self.sentence_id, self.text_id, self.table, self.translation_id))

class SourceText(TextPair):
    """The pair of the inserted text"""
    def __init__(self, table, inputfile, con):
        super().__init__(table, inputfile)
        #Insert this text to the text_ids table
        con.query("INSERT INTO text_ids (title) values(%s)", (self.inputfile,),commit=True)
        self.sentence_id = GetLastValue(con.FetchQuery("SELECT max(sentence_id) FROM {}".format(self.table)))
        self.current_align_id    = GetLastValue(con.FetchQuery("SELECT max(align_id) FROM {}".format(self.table)))
        self.text_id     = GetLastValue(con.FetchQuery("SELECT max(id) FROM text_ids"))
        self.translation_id = None


    def LoopThroughSegments(self):
        for segment in self.alignsegments:
            #Split each segment into lines (line=word with all the morphological and syntactic information)
            self.current_align_id    += 1
            self.sentence_id += 1
            self.ProcessWordsOfSegment(segment.splitlines())
            self.bar.next()

class Translation(TextPair):
    """The pair of the inserted text"""
    def __init__(self, table, inputfile, con, sl_textid, sltable):
        super().__init__(table, inputfile)
        self.status = 'translation'
        self.text_id = sl_textid
        self.align_ids = con.FetchQuery("SELECT DISTINCT align_id FROM {} WHERE text_id = %s order by align_id".format(sltable),(self.text_id,))
        con.query("INSERT INTO translation_ids (title, sourcetext_id) VALUES(%s, %s)",(inputfile,self.text_id,),commit=True)
        self.translation_id  = GetLastValue(con.FetchQuery("SELECT max(id) FROM translation_ids WHERE sourcetext_id = %(sid)s",{'sid':self.text_id}))
        self.sentence_id = GetLastValue(con.FetchQuery("SELECT max(sentence_id) FROM {}".format(self.table)))
        if len(self.alignsegments) != len(self.align_ids):
            raise AlignMismatch('The number of segments differs from the number in the source text: {}/{}'.format(len(self.alignsegments),len(self.align_ids)))

    def LoopThroughSegments(self):
        for idx, align_id in enumerate(self.align_ids):
            self.current_align_id = align_id[0]
            segment = self.alignsegments[idx]
            self.sentence_id += 1
            self.ProcessWordsOfSegment(segment.splitlines())
            self.bar.next()

def AddRow(columns, align_id, sentence_id, text_id, table, translation_id = None):
    """Collect the data about a single word"""
    if len(columns) < 7:
        #If an empty segment encountered
        print('Note: an empty segment encountered at align_id {}'.format(align_id))
        row = {'align_id' : align_id, 'sentence_id' : sentence_id, 'text_id' : text_id, 'tokenid' : 1, 'token' : 'EMPTYSEGMENT', 'lemma' : 'EMPTYSEGMENT', 'pos' : 'EMPTYSEGMENT', 'feat' : 'EMPTYSEGMENT', 'head' : 0, 'deprel' : 'EMPTY'}
    else:
        #If this is a word with information, initialize a new row
            if table == 'ru_conll':
                row = {'align_id'    : align_id,
                       'sentence_id' : sentence_id,
                       'text_id'     : text_id,
                       'tokenid'     : columns[0],
                       'token'       : columns[1],
                       'lemma'       : columns[2],
                       'pos'         : columns[4],
                       'feat'        : columns[5],
                       'head'        : columns[6],
                       'deprel'      : columns[7]}
            elif table == 'fi_conll':
                row =  {'align_id'    : align_id,
                        'sentence_id' : sentence_id,
                        'text_id'     : text_id,
                        'tokenid'     : columns[0],
                        'token'       : columns[1],
                        'lemma'       : columns[2],
                        'pos'         : columns[4],
                        'feat'        : columns[6],
                        'head'        : columns[8],
                        'deprel'      : columns[10]}
    if translation_id:
        row['translation_id'] = translation_id

    return row

def TrimList(clist):
    """Checks if the first or the  last element of a list is empty"""
    try:
        if clist[0] == '':
            clist = clist[1:]
        if clist[-1] == '':
            clist = clist[:-1]
    except IndexError:
        clist = clist
    return clist

def GetLastValue(row):
    """Returns the first vacant index from the database"""
    try:
        if row[0][0] == None:
            return 0
        else:
            return row[0][0]
    except TypeError:
        return 0

def BulkInsert():
    """Hardcode some paths and make a batch insert"""
    #Set the paths before running:
    #sl = 'ru'
    #tl = 'fi'
    sl = 'fi'
    tl = 'ru'
    sltable = sl + '_conll'
    tltable = tl + '_conll'
    sl_dirprefix = '/home/juho/corpora2/syntparfin2/' + sltable
    tl_dirprefix = '/home/juho/corpora2/syntparfin2/' + tltable
    pairs = list()
    for filename in os.listdir(sl_dirprefix):
        pairs.append(dict())
        pairs[-1]['sl'] = sl_dirprefix + "/" + filename
        pairs[-1]['tl'] = tl_dirprefix + "/" + filename.replace('_'+sl,'_'+tl)
    for pair in pairs:
        print('Inserting {} and its translation...'.format(pair['sl']))
        InsertPair('syntparfin2',pair['sl'],pair['tl'], sltable, tltable)

def InsertPair(dbname=None,slfile=None,tlfile=None,sl_tablename=None,tl_tablename=None):
    """Method for inserting one file pair either according to cmdline arguments or by function arguments"""
    if not dbname:
        #If not run from another method, get command line input:
        try:
            dbname = sys.argv[1]
            slfile = sys.argv[2]
            tlfile = sys.argv[3]
            sl_tablename = sys.argv[4] + '_conll'
            tl_tablename = sys.argv[5] + '_conll'
        except IndexError:
            raise ArgumentError('Usage: {} <database name> <sl file> <tl file> <source language> <target language>'.format(sys.argv[0]))

    con = psycopg(dbname,'juho')

    sl  = SourceText(sl_tablename, slfile, con)
    sl.CollectSegments()
    sl.InsertToDb(con)

    tl  = Translation(tl_tablename, tlfile, con, sl.text_id, sl.table)
    tl.CollectSegments()
    tl.InsertToDb(con)

#============================================================

if __name__ == "__main__":
    if sys.argv[1] == 'bulk':
        BulkInsert()
    else:
        InsertPair()
