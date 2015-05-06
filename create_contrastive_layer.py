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

def cleardata(con):
    con.insertquery("UPDATE fi_conll SET contr_deprel = NULL")
    con.insertquery("UPDATE ru_conll SET contr_deprel = NULL")

def syntsubj1(con):
    """1. deprel = predik + form=inf --> syntsubj"""
    con.insertquery("UPDATE ru_conll SET contr_deprel = 'syntsubj' WHERE pos = 'V' AND feat LIKE %s AND deprel = %s",('Vmn---%','предик'))
    logging.info("UPDATED {} rows in {}".format(con.cur.rowcount, con.dbname))

def csubj1(con):
    """1.csubj-cop > csubj. 2. csubj > syntsubj"""
    con.insertquery("""UPDATE fi_conll SET contr_deprel = 'syntsubj' WHERE (deprel = 'csubj' OR deprel = 'csubj-cop')
                    AND feat LIKE %s
                    AND feat NOT LIKE %s""",('%Inf1','%POSS%'))
    logging.info("UPDATED {} rows in {}".format(con.cur.rowcount, con.dbname))

def TDTsemsubj1(con):
    """Reanalyze those tdt's nsubjs that relate to a necessive structure"""
    #Make a search object and try to find all words that match the riteria defined in the search type
    thisSearch = Search(con.dbname)
    Db.searched_table = 'fi_conll'
    thisSearch.subquery = "SELECT align_id FROM fi_conll WHERE deprel = %s AND FEAT like %s"
    thisSearch.searchtype= "semsubj_gen"
    thisSearch.subqueryvalues=('nsubj','%CASE_Gen%')
    thisSearch.find()
    ids = collectmatchids(thisSearch.matches.items())
    #Update the database according to matches
    print('Updating...')
    con.insertquery('UPDATE fi_conll SET contr_deprel = %s WHERE id in %s',('semsubj', ids))
    logging.info("UPDATED {} rows in {}".format(con.cur.rowcount, con.dbname))

def suboord1(con):
    """Reanalyze SN's way of determining head-dependent relations in suboordination"""
    thisSearch = Search(con.dbname)
    Db.searched_table = 'ru_conll'
    thisSearch.subquery = "SELECT align_id FROM ru_conll WHERE deprel = %s"
    thisSearch.lemmas_or_tokens = 'deprel'
    thisSearch.searchstring = 'подч-союзн'
    thisSearch.subqueryvalues=('подч-союзн',)
    thisSearch.find()
    matchitems = thisSearch.matches.items()
    sql = "UPDATE ru_conll SET contr_deprel = CASE id"
    sqlvals = list()
    idvals = list()
    logging.info('Starting the update process.')
    #First, set deprel
    for key, matches in matchitems:
        for match in matches:
            nonconj = match.matchedword
            try:
                conj = match.matchedsentence.words[nonconj.head]
                #conj
                sql += """ WHEN %s THEN %s"""
                sqlvals.append(conj.dbid)
                sqlvals.append('conj')
                idvals.append(conj.dbid)
                #nonconj
                sql += """ WHEN %s THEN %s"""
                sqlvals.append(nonconj.dbid)
                sqlvals.append('carg')
                idvals.append(nonconj.dbid)
            except KeyError:
                logging.info('Key error with sentence id {}'.format(match.matchedsentence.sentence_id))
    #Then set heads
    sql += " END, contr_head = CASE id"
    for key, matches in matchitems:
        for match in matches:
            nonconj = match.matchedword
            try:
                conj = match.matchedsentence.words[nonconj.head]
                #conj
                sql += """ WHEN %s THEN %s"""
                sqlvals.append(conj.dbid)
                sqlvals.append(nonconj.tokenid)
                #nonconj
                sql += """ WHEN %s THEN %s"""
                sqlvals.append(nonconj.dbid)
                sqlvals.append(conj.head)
            except:
                logging.info('Key error with sentence id {}'.format(match.matchedsentence.sentence_id))
    sql += " END WHERE id in %s"
    sqlvals.append(tuple(idvals))
    con.insertquery(sql,tuple(sqlvals))
    logging.info("UPDATED {} rows in {}".format(con.cur.rowcount, con.dbname))

def collectmatchids(matchitems):
    ids = list()
    for key, matches in matchitems:
        for match in matches:
            ids.append(match.matchedword.dbid)
    return tuple(ids)


#Initialize a logger
root = logging.getLogger()
root.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)

fh = logging.FileHandler('logfile')
fh.setLevel(logging.DEBUG)

fh.setFormatter(formatter)
ch.setFormatter(formatter)
root.addHandler(fh)
root.addHandler(ch)


logging.info("Establishing connections...")
pfcon = mydatabase('syntparfin','juho')
prcon = mydatabase('syntparrus','juho')

logging.info("Clearing all data from contr_deprel")
cleardata(pfcon)
cleardata(prcon)
logging.info("Cleared.")

logging.info("Creating syntsubj for SN")
syntsubj1(pfcon)
syntsubj1(prcon)

logging.info("Creating syntsubj for TDT")
logging.info("Making csubj-cop csubj and all csubjs syntsubj")
csubj1(pfcon)
csubj1(prcon)

logging.info('Make TDT:s genitive nsubjects semsubjects')
TDTsemsubj1(pfcon)
TDTsemsubj1(prcon)

logging.info('Reanalyzing SNs subordinate clauses')
suboord1(pfcon)
suboord1(prcon)

logging.info('Done.')
