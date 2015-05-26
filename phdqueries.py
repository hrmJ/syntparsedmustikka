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


def BuildGroupString(match,attribute,accepted_dependencies=list()):
    """This methods constructs strings that 
    can be used in statistical analysis. The created strings represent 
    the nuclei that are dependent on the same head as the matched nucleus"""
    groupmembers = dict()
    for tokenid, word in match.matchedsentence.words.items():
        #Mark the head with square brackets
        if tokenid == match.matchedword.head:
            groupmembers[tokenid] = "[{}]".format(getattr(word,attribute))
        # Pick all the word objects that have the same head and that are not punctuation marks
        if word.head == match.matchedword.head and word.token not in string.punctuation:
            if tokenid == match.matchedword.tokenid:
                groupmembers[tokenid] = "<{}>".format(getattr(word,attribute))
            else:
                #if a list of accepted deprelations is defined, take into account only those
                if accepted_dependencies:
                    if word.deprel in accepted_dependencies:
                        groupmembers[tokenid] = getattr(word,attribute)
                #Don't take into account conjunctions
                elif word.deprel not in ('cc','conj'):
                    groupmembers[tokenid] = getattr(word,attribute)
    # Build a string from the attributes
    for gmkey in sorted(map(int,groupmembers)):
        try:
            groupstring += "|" + groupmembers[gmkey]
        except:
            groupstring = groupmembers[gmkey]
    return groupstring

def joinidlist(idrows):
    """Flatten the lists from database"""
    idlist =  list(itertools.chain(*idrows))
    idlist = ','.join(map(str, idlist)) 
    return idlist

def BuildDataGroupString(db,table):
    "Define a shortcut string for different data groups"
    if db=='syntparfin' and table == 'fi_conll':
        return 'FS'
    elif db=='syntparfin' and table == 'ru_conll':
        return 'RT'
    elif db=='syntparrus' and table == 'fi_conll':
        return 'FT'
    elif db=='syntparrus' and table == 'ru_conll':
        return 'RS'
    else:
        return 'unknown'

def DetermineClausesLastWordId(match):
    """A method that calculates the tokeid of the last word in the matched clause"""
    sentencekeys =  sorted(map(int,match.matchedsentence.words))
    #loop starting from the index of the matched word
    for idx in sentencekeys[int(match.matchedword.tokenid):]:
        pass


def AnalyzeTimeAdvlData1(search):
    """Annotate material for use in phd"""
    #Connect to database
    con = mydatabase('matches','juho')
    print('Inserting data analysis to database')
    #Loop through all the matches in a search object
    i = 0
    for alignid, matchlist in search.matches.items():
        for match in matchlist:
            #Build human readable strings:
            match.BuildSentencePrintString()
            #insert values to the metadata table
            SQL = "INSERT INTO metadata (hlsentence, sentence, sourcetext, datagroup, db, dbtable,matched_sentence_id,matched_word_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
            con.insertquery(SQL,(match.matchedsentence.printstring,
                                match.matchedsentence.cleanprintstring,
                                match.sourcetextid,
                                BuildDataGroupString(search.queried_db,search.queried_table),
                                search.queried_db,
                                search.queried_table,
                                match.matchedsentence.sentence_id,
                                match.matchedword.dbid
                                )) 

            #get the id of the inserted metadata item
            SQL = "SELECT max(id) FROM metadata"
            linkid = con.nondictquery(SQL)
            linkid = linkid[0][0]
            SQL = "INSERT INTO valency_information (linkid, valency_chain, lemma_chain, pos_chain, head_type, narrowed_valency_chain) VALUES (%s,%s,%s,%s,%s,%s)"
            #Define some special sets of dependency relations
            deprellimits1 = ('dobj','nommod','advmod')
            #insert values to the valency_information table
            con.insertquery(SQL,(linkid,BuildGroupString(match,'deprel'),
                                BuildGroupString(match,'lemma'),
                                BuildGroupString(match, 'pos'),
                                match.matchedsentence.words[match.matchedword.head].deprel,
                                BuildGroupString(match, 'deprel',deprellimits1)
                                )) 
        i += 1
        print('Analyzed {}/{} matches.'.format(i,len(search.matches.items())), end='\r')
    print('')
    print('Analysis completed.')
    print('')

def UpdateHeadDeprelToDB(table):
    """Insert information about the deprel of the head of each word into database"""
    con = mydatabase('syntparfin','juho')
    sentence_ids = con.nondictquery('SELECT DISTINCT sentence_id FROM {}'.format(table))
    i=0
    for sid in sentence_ids:
        tokens = con.nondictquery('SELECT tokenid, head FROM {} WHERE sentence_id = %s order by tokenid'.format(table),(sid[0],))
        for token in tokens:
            heads_deprel = con.nondictquery('SELECT deprel, pos, feat FROM {} WHERE sentence_id = %s AND tokenid = %s'.format(table),(sid[0],token[1]))
            if heads_deprel:
                con.insertquery('UPDATE {} SET heads_deprel = %s, heads_pos = %s, heads_feat = %s WHERE sentence_id = %s AND tokenid = %s'.format(table),(heads_deprel[0][0],heads_deprel[0][1],heads_deprel[0][2], sid[0], token[0]))
        i += 1
        print('{}/{} sentences updated'.format(i,len(sentence_ids)), end='\r')


def tmevalues(lang):
    """return a list of dicts to find tmes"""
    #Restrict the number of align ids by means of sql
    #1.1 condition about the lemma and the deprel of the word
    if lang == 'fi':
        deprel= ('nsubj','nsubj-cop','ROOT')
    elif lang == 'ru':
        deprel= ('предик','дат-субъект')
    allwords = Csvlist('/home/juho/phdmanuscript/clausinittime/tme_{}.csv'.format(lang))
    ConditionColumns = list()
    for row in allwords.aslist:
        ConditionColumns.append({'lemma':(row[0],), '!deprel':deprel})
    return ConditionColumns
