#! /usr/bin/env python
#Import modules
import codecs
import random
import csv
import sys
import os
from collections import defaultdict
from lxml import etree
import string
import re
from termcolor import colored
from tools.objecttools import savepickle, loadpickle
#local modules
from dbmodule import mydatabase, psycopg
from menus import Menu, multimenu, yesnomenu 
from itertools import chain
from progress.bar import Bar
from texttable import Texttable, get_color_string, bcolors
import time
import datetime
from statistics import mean, median
#from analysistools import InsertDeprelColumns, ListSisters

class Db:
    """ A class to include some shared properties for the search and
    the match classes"""
    # What is the language table used in the queries
    searched_table = ''
    #a connection to db
    #con = mydatabase('syntparfin','juho')

class ConstQuery:
    """Some often used queries can be saved as instances of this class"""
    # What is the language table used in the queries
    independentByLemma2 ="""SELECT lemmaQ.align_id FROM 
                            (SELECT * FROM {0} WHERE lemma = %s) as lemmaQ, {0}
                                WHERE {0}.tokenid = lemmaQ.head AND 
                                {0}.sentence_id = lemmaQ.sentence_id AND
                                {0}.deprel='ROOT'""".format('ru_conll')

    independentByLemma ="""SELECT lemmaQ.id, lemmaQ.align_id, lemmaQ.text_id, lemmaQ.sentence_id FROM 
                            (SELECT * FROM {0} WHERE lemma = %s) as lemmaQ, {0}
                                WHERE {0}.tokenid = lemmaQ.head AND 
                                {0}.sentence_id = lemmaQ.sentence_id AND
                                {0}.deprel='ROOT'""".format('ru_conll')

class Search:
    """This is the very
    basic class that is used to retrieve data from the corpus"""
    all_searches = []
    def __init__(self,queried_db='',askname=True):
        """Initialize a search object. 
        ----------------------------------------
        attributes:
        searchtype = this helps to determine search-specific conditions
        matches = The matches will be saved as lists in a dict with align_ids as keys.
        """
        self.matches = defaultdict(list)
        #Save the search object to a list of all conducted searches during the session
        Search.all_searches.append(self)
        # save an id for the search for this session
        self.searchid = id(self)
        #Ask a name for the search (make this optional?)
        if askname:
            self.name = input('Give a name for this search:\n\n>')
        else:
            self.name = 'unnamed_{}'.format(len(Search.all_searches))
        self.searchtype = 'none'
        #Make a dict to contain column_name: string_value pairs to be matched
        self.ConditionColumns = list()
        #Make a dict containing the psycopg2 string reference and its desired value
        self.subqueryvalues = dict()
        #Initiate an attribute that will be dealing with the word's head's parameters
        self.headcond = dict()
        #Initiate an attribute that will be dealing with the word's dependents' parameters
        self.depcond = dict()
        #Record information about db
        self.queried_db = queried_db
        self.queried_table = Db.searched_table
        #Change the default connection:
        Db.con = mydatabase(queried_db,'juho')
        #Initialize a log for errors associated with this search
        self.errorLog = ''
        #By default, make monoconcordances
        self.isparallel = False
        #Count the numnber of actual matches
        self.absolutematchcount = 0

    def Save(self):
        """Save the search object as a pickle file"""
        savepickle(self.filename,self)
        input('Pickle succesfully saved.')

    def BuildSubQuery(self):
        """Builds a subquery to be used in the find method"""
        MultipleValuePairs = ''
        #This is to make sure psycopg2 uses the correct %s values
        sqlidx=0
        for ivaluedict in self.ConditionColumns:
            if MultipleValuePairs:
                MultipleValuePairs += " OR "
            MultipleValuePairs += "({})".format(self.BuildSubqString(ivaluedict,sqlidx))
            sqlidx += 1
        self.subquery = """SELECT {} FROM {} WHERE {} """.format(self.toplevel, Db.searched_table,MultipleValuePairs)

    def BuildSubqString(self, ivaluedict,parentidx):
        """ Constructs the actual condition. Values must be TUPLES."""
        condition = ''
        sqlidx=0
        for column, value in ivaluedict.items():
            #Make sure the user gives the values as tuples (excluding fuzzy matches)
            if column[0] not in ('?','#') and not isinstance(value,tuple):
                raise TypeError('The values in the ConditionColumn lists dict must be tuples, see {}:{}'.format(column,value))
            if condition:
                condition += " AND "
            #This is to make sure psycopg2 uses the correct %s values
            sqlRef = '{}cond{}'.format(parentidx,sqlidx)
            #If this is a neagtive condition
            if column[0] == '!':
                condition += "{} not in %({})s".format(column[1:],sqlRef)
            #If this is a regexp condition. Note, that the values of a regexpcond.dict must be simple strings, not tuples
            elif column[0] == '#':
                condition += "{} ~ %({})s".format(column[1:],sqlRef)
            #If this is a fuzzy condition. Note, that the values of a fuzzycond.dict must be simple strings, not tuples
            elif column[0] == '?':
                condition += "{} LIKE %({})s".format(column[1:],sqlRef)
            else:
                condition += "{} in %({})s".format(column,sqlRef)
            self.subqueryvalues[sqlRef] = value
            sqlidx += 1
        return condition

    def find(self):
        """Query the database according to instructions from the user
        The search.subquery attribute can be any query that selects a group of align_ids
        From the syntpar...databases
        """
        sql_cols = "tokenid, token, lemma, pos, feat, head, deprel, align_id, id, sentence_id, text_id"
        sqlq = "SELECT {0} FROM {1} WHERE {3} in ({2}) order by {3}, id".format(sql_cols, Db.searched_table, self.subquery, self.toplevel)
        if self.limited:
            #If the user wants to limit the search e.g. for testing large corpora
            sqlq = "SELECT {0} FROM {1} WHERE {4} in ({2}) order by {4}, id LIMIT {3}".format(sql_cols, Db.searched_table, self.subquery, self.limited, self.toplevel)
        start = time.time()
        print("Starting the query...")
        wordrows = Db.con.dictquery(sqlq,self.subqueryvalues)
        print("Query completed in {} seconds".format(time.time()-start))
        if wordrows:
            start = time.time()
            print('Starting to analyze {} rows...'.format(len(wordrows)))
            self.bar = Bar('Processing words and sentences...')
            if self.toplevel=="align_id":
                self.pickFromAlign_ids(wordrows)
                if self.isparallel:
                    self.FindParallelSegmentsAfterwards()
            elif self.toplevel=="sentence_id":
                self.PickFromSentence_ids(wordrows)
            self.bar.finish()
            print('Analysis completed in {} seconds, {} matches found!'.format(time.time()-start, self.absolutematchcount))
        else:
            return input('Nothing found..')

    def FindMonoLing(self):
        """Query the database OF A MONOLINGUAL corpus according to instructions from the user.
        The search.subquery attribute can be any query that selects a group of sentence_ids
        From the databases.
        """
        sql_cols = "tokenid, token, lemma, pos, feat, head, deprel, align_id, id, sentence_id, text_id"
        sqlq = "SELECT {0} FROM {1} WHERE align_id in ({2}) order by align_id, id".format(sql_cols, Db.searched_table, self.subquery)
        if self.limited:
            #If the user wants to limit the search e.g. for testing large corpora
            sqlq = "SELECT {0} FROM {1} WHERE align_id in ({2}) order by align_id, id LIMIT {3}".format(sql_cols, Db.searched_table, self.subquery, self.limited)
        wordrows = Db.con.dictquery(sqlq,self.subqueryvalues)
        print('Analyzing...')
        if wordrows:
            self.pickFromAlign_ids(wordrows)
            if self.isparallel:
                self.FindParallelSegmentsAfterwards()
        else:
            return input('Nothing found..')

    def pickFromAlign_ids(self, wordrows):
        """Process the data from database query
        This is done word by word."""
        self.aligns = dict()
        for wordrow in wordrows:
            #If the first word of a new align unit is being processed
            if wordrow['align_id'] not in self.aligns:
                #If this is not the first word of the first sentence:
                if self.aligns:
                    #Check for matching words in the last sentence of the previous align unit
                    self.processWordsOfSentence(previous_align,previous_sentence)
                    #Process all the sentences in the previous align unit to collect the matches
                    self.ProcessSentencesOfAlign(previous_align)
                #Initialize the new align unit of wich this is the first word
                self.aligns[wordrow['align_id']] = dict()
                previous_align = wordrow['align_id']
            #If the first word of a new sentence is being processed
            if wordrow['sentence_id'] not in self.aligns[wordrow['align_id']]:
                #If this sentence id not yet in the dict of sentences, add it
                if self.aligns and self.aligns[previous_align]:
                    #If this is not the first word of the first sentence:
                    #Process the previous sentence of this align unit
                    #ORDER OF THIS WORD DICT!!
                    self.processWordsOfSentence(wordrow['align_id'],previous_sentence)
                # Add this sentence to this align unit
                self.aligns[wordrow['align_id']][wordrow['sentence_id']] = Sentence(wordrow['sentence_id'])
                previous_sentence = wordrow['sentence_id']
            # Add all the information about the current word as a Word object to the sentence
            self.aligns[wordrow['align_id']][wordrow['sentence_id']].words[wordrow['tokenid']] = Word(wordrow)
        #Finally, process all the sentences in the last align unit that included a match or matches (if the original query didn't fail)
        if wordrows:
            self.processWordsOfSentence(previous_align,previous_sentence)
            self.ProcessSentencesOfAlign(previous_align)

    def PickFromSentence_ids(self, wordrows):
        """Process the data from database query
        This is done word by word."""
        self.sentences = dict()
        for wordrow in wordrows:
            #If the first word of a new sentence is being processed
            if wordrow['sentence_id'] not in self.sentences:
                #If this sentence id not yet in the dict of sentences, add it
                if self.sentences:
                    #If this is not the first word of the first sentence:
                    #Process the previous sentence of this align unit
                    #ORDER OF THIS WORD DICT!!
                    self.processWordsOfSentence(0,previous_sentence)
                # Add this sentence to this align unit
                self.sentences[wordrow['sentence_id']] = Sentence(wordrow['sentence_id'])
                previous_sentence = wordrow['sentence_id']
            # Add all the information about the current word as a Word object to the sentence
            self.sentences[wordrow['sentence_id']].words[wordrow['tokenid']] = Word(wordrow)
        #Finally, process all the words in the last sentence (if the original query didn't fail)
        if wordrows:
            self.processWordsOfSentence(0,previous_sentence)

    def processWordsOfSentence(self,alignkey,sentencekey):
        """ Process every word of a sentence and check if a search condition is met.
        The purpose of this function is to simplify the pickFromAlign_ids function"""
        # The sentence is processed word by word
        if self.toplevel == "sentence_id":
            sentence = self.sentences[sentencekey]
        elif self.toplevel == "align_id":
            sentence = self.aligns[alignkey][sentencekey]
        for wkey in sorted(map(int, sentence.words)):
            word = sentence.words[wkey]
            if self.evaluateWordrow(word,sentence):  
                #if the evaluation function returns true
                if self.toplevel == "sentence_id":
                    sentence.matchids.append(word.tokenid)
                    self.matches[sentencekey].append(MonoMatch(word.tokenid,sentence))
                    self.absolutematchcount += 1
                elif self.toplevel == "align_id":
                    sentence.matchids.append(word.tokenid)
        self.bar.next()


    def ProcessSentencesOfAlign(self, alignkey):
        """ Process all the sentences in the previous align unit and check for matches
           variables:
           alignkey = the key of the align segment to be processed
           """
        for sentence_id in sorted(map(int,self.aligns[alignkey])):
            #Process all the matches in the sentence that contained one or more matches
            for matchid in self.aligns[alignkey][sentence_id].matchids:
                self.matches[alignkey].append(Match(self.aligns[alignkey],matchid,sentence_id,alignkey))
                self.absolutematchcount += 1

    def evaluateWordrow(self, word,sentence):
        'Test a word (in a sentence) according to criteria'
        #Iterate over the list of the sepcified column value pairs
        for MultipleValuePair in self.ConditionColumns:
            pairmatch=True
            for column, value in MultipleValuePair.items():
                #If this is a negative condition:
                if column[0] == '!':
                    if getattr(word, column[1:]) in value:
                        #if the requested value of the specified column is what's not being looked for, regard this a non-match
                        pairmatch = False
                #If this is a fuzzy condition:
                elif column[0] == '?':
                    if value.replace('%','') not in getattr(word, column[1:]):
                        #if the requested value of the specified column isn't what's being looked for, regard this a non-match
                        pairmatch = False
                elif column[0] == '#':
                    pattern  = re.compile(value)
                    if not pattern.match(getattr(word,column[1:])):
                        #if the requested value of the specified column isn't what's being looked for, regard this a non-match
                        pairmatch = False
                else:
                    if getattr(word, column) not in value:
                        #if the requested value of the specified column isn't what's being looked for, regard this a non-match
                        pairmatch = False
            if pairmatch:
                #if one of the conditions matched, accept this and stop testing
                break
        if not pairmatch:
            return False
        #-------------------------------------------------------------------------------------
        #Test conditions based on the head of the word
        if self.headcond:
            #To test if this has no head at all:
            isRoot=True
            #use this variable to test if the head fulfills the criteria
            #Assume that the head DOES fulfill the criteria
            headfulfills=True
            for wkey in sorted(map(int,sentence.words)):
                wordinsent = sentence.words[wkey]
                if word.head == wordinsent.tokenid:
                    #When the loop reaches the head of the word
                    isRoot = False
                    if self.headcond['column'][0] == '!':
                        #If this is a negative condition:
                        if getattr(wordinsent, self.headcond['column'][1:]) in self.headcond['values']:
                            #If condition negative and the head of the examined word matches the condition:
                            headfulfills = False
                            break
                    else:
                        #If this is a positive condition:
                        if getattr(wordinsent, self.headcond['column']) not in self.headcond['values']:
                            #If condition positive and the head of the examined word doesn't match the condition:
                            headfulfills = False
                            break
            if not headfulfills:
                #If the head of the word did not meet the criteria
                return False
            if isRoot:
                #If this word has no head, return False
                return False
        #-------------------------------------------------------------------------------------
        #Test conditions based on the dependents of the word
        if self.depcond:
            #use this variable to test if ALL the DEPENDENTS fulfill the criteria
            #Assume that the dependents DO fulfill the criteria
            headfulfills=True
            for wkey in sorted(map(int,sentence.words)):
                wordinsent = sentence.words[wkey]
                if wordinsent.head == word.tokenid:
                    #When the loop reaches a dependent of the examined word
                    if self.depcond['column'][0] == '!':
                        #If this is a negative condition:
                        if getattr(wordinsent, self.depcond['column'][1:]) in self.depcond['values']:
                            headfulfills = False
                            break
                    else:
                        #If this is a positive condition:
                        if getattr(wordinsent, self.depcond['column']) not in self.depcond['values']:
                            headfulfills = False
                            break
            if not headfulfills:
                #If the head of the word did not meet the criteria
                return False
        #if all tests passed, return True
        return True

    def FetchPreviousAlign(self,align_id):
        """Fetches the previous align unit from the db"""
        sql_cols = "tokenid, token, lemma, pos, feat, head, deprel, align_id, id, sentence_id, text_id"
        sqlq = "SELECT {0} FROM {1} WHERE align_id = {2} order by align_id, id".format(sql_cols, Db.searched_table, align_id)
        wordrows = Db.con.dictquery(sqlq)

    def listMatchids(self):
        """Returns a tuple of all the DATABASE ids of the matches in this Search"""
        idlist = list()
        for key, matches in self.matches.items():
            for match in matches:
                idlist.append(match.matchedword.dbid)
        self.idlist = tuple(idlist)
        return self.idlist

    def ListMatchLemmas(self):
        """fetch ditinctly the lemmas from sl"""
        #if the lemmas have not yet been listed:
        try:
            self.matchlemmas = self.matchlemmas
            if not self.matchlemmas:
                raise(AttributeError)
        except AttributeError:
            print('Fetching the lemmas, please wait...')
            self.listMatchids()
            con = psycopg(self.queried_db,'juho')
            self.listMatchids()
            sqlq = "SELECT DISTINCT lemma FROM {table} WHERE id in %(ids)s".format(table = self.queried_table)
            ('Fetching all the source lemmas')
            self.matchlemmas = con.FetchQuery(sqlq,{'ids':self.idlist})
            self.matchlemmas = list(chain.from_iterable(self.matchlemmas))

    def ListMatchLemmaTranslations(self):
        """
        Ask the user to specify probable translation for each lemma of the matches in the search.
        
        This is a rather temporary method that will be removed and made database-driven when I have time"""
        self.ListMatchLemmas()
        matchlemmadict = dict()
        askmenu =  multimenu({'n':'insert next possible match in target language','q':'Finnish inserting possible matches for this word'})
        for lemma in self.matchlemmas:
            matchlemmadict[lemma] = list()
            while askmenu.prompt_valid(definedquestion = 'Source lemma: {}'.format(lemma)) == 'n':
                matchlemmadict[lemma].append(input('Give the possible matching lemma:\n>'))
        self.matchlemmas = matchlemmadict

    def FindParallelSegmentsAfterwards(self):
        """This is used for searches done in the phase of development where originally 
        only one language is retrieved"""
        #Make sure the search is connected to the right database:
        con = psycopg(self.queried_db,'juho')

        #Set the right target language
        if self.queried_table == 'fi_conll':
            self.parallel_table = 'ru_conll'
        elif self.queried_table == 'ru_conll':
            self.parallel_table = 'fi_conll'

        sql_cols = "tokenid, token, lemma, pos, feat, head, deprel, align_id, id, sentence_id, text_id, contr_deprel, contr_head"
        sqlq = "SELECT {0} FROM {1} WHERE align_id in %(ids)s order by align_id, id".format(sql_cols, self.parallel_table)
        print('Quering the database, this might take a while...')
        wordrows = con.FetchQuery(sqlq,{'ids':tuple(self.matches.keys())},usedict=True)
        print('Analyzing...')
        #for matchindex, matches in self.matches.items():
        self.parallel_aligns = dict()
        for wordrow in wordrows:
            if wordrow['align_id'] not in self.parallel_aligns:
                self.parallel_aligns[wordrow['align_id']] = dict()
            if wordrow['sentence_id'] not in self.parallel_aligns[wordrow['align_id']]:
                self.parallel_aligns[wordrow['align_id']][wordrow['sentence_id']] = TargetSentence(wordrow['sentence_id'])
            self.parallel_aligns[wordrow['align_id']][wordrow['sentence_id']].words[wordrow['tokenid']] = Word(wordrow)
        #print('Assign the correct target segment for each match...')
        for align_id, matches in self.matches.items():
            for match in matches:
                match.parallelcontext = self.parallel_aligns[align_id]
        #print('Done.')

    def CountMatches(self,filters=False):
        """Count the number of matches and filter by criteria"""
        self.matchcount = 0
        for key, matches in self.matches.items():
            for match in matches:
                if filters:
                    #Apply a filter:
                    match.WillBeProcessed = True
                    for attribute, value in filters.items():
                        try:
                            if getattr(match,attribute) != value:
                                match.WillBeProcessed = False
                        except AttributeError:
                            #If the match object DOESNT have the attribute, accept it
                            pass
                    if match.WillBeProcessed:
                        self.matchcount += 1
                else:
                    self.matchcount += 1

    def AlignAtMatch(self):
        """Semi-manually go through all the matches of the search
        and pick the word that is the closest to the matching word of each match"""
        #matchestoprocess.append(match)
        #Test if potential translations already listed
        try:
            if not 'dict' in str(type(self.matchlemmas)):
                self.ListMatchLemmaTranslations()
        except AttributeError:
                self.ListMatchLemmaTranslations()
        self.CountMatches({'rejectreason':'','postprocessed':True,'aligned':False})
        bar = Bar('Processing', max=self.matchcount)
        elapsedtimes = list()
        done = 0
        for key, matches in self.matches.items():
            for match in matches:
                if match.WillBeProcessed:
                    start = time.time()
                    #####
                    match.LocateTargetWord(self)
                    #####
                    done +=1
                    elapsedtimes = PrintTimeInformation(elapsedtimes, start,done,self.matchcount,bar)
                    cont = input('Press enter to continue or s to save the search object')
                    if cont == 's':
                        self.Save()
        bar.finish()

    def PickRandomMatch(self):
        """Return a random match"""
        return self.matches[random.choice(list(self.matches.keys()))][0]

    def InsertTmeToResults(self,tablename='tme',applyfilter=True,nolargecontext=False):
        """Insert to exzternal database"""
        #Set parameters for source and target languages
        if self.queried_table == 'fi_conll':
            sl = 'fi'
            tl = 'ru'
        elif self.queried_table == 'ru_conll':
            sl = 'ru'
            tl = 'fi'

        #Get all the matches that have not been rejected but have been aligned
        if applyfilter:
            self.CountMatches({'rejectreason':'','postprocessed':True,'aligned':True})
        else:
            self.CountMatches({'rejectreason':''})
        #Connect to dbs
        con = psycopg('results','juho')
        con2 = psycopg(self.queried_db,'juho')
        all_texts = con2.FetchQuery('SELECT id, title, origtitle, author, translator, origyear, transyear FROM text_ids',usedict=True)
        # Create separate deprel tables
        if sl == 'ru':
            pass
            #InsertDeprelColumns('ru')
        #if sl == 'fi':
        #    InsertDeprelColumns('fi')

        #Set the values
        rowlist = list()
        rowlist_ru_deprels = list()
        rowlist_fi_deprels = list()
        bar = Bar('Preparing and analyzing the data', max=self.matchcount)
        errorcount=0
        inscount = 0
        for align_id, matchlist in self.matches.items():
            for match in matchlist:
                if match.WillBeProcessed:
                    #create a string for the align unit and the sentences
                    if match.DefinePosition1():
                        match.BuildContextString(nolargecontext)
                        row = dict()
                        row_ru_deprels = dict()
                        row_fi_deprels = dict()
                        metadata = GetMetadata(match.matchedword.sourcetextid,all_texts)
                        #hackyfixes:
                        row['tl_coordcombined'] = None
                        row['tl_headfeat'] = None
                        row['tl_deplemmas'] = None
                        row['tl_prevlemma'] = None
                        row['tl_matchfeat'] = None
                        #---
                        row['sl'] = sl
                        row['tl'] = tl
                        row['sl_sentence'] = match.matchedsentence.printstring
                        row['tl_sentence'] = SetUncertainAttribute('',match,'parallelsentence','printstring')
                        row['sl_clause'] = match.matchedclause.printstring
                        row['tl_clause'] = SetUncertainAttribute('',match,'parallelclause','printstring')
                        row['slpos'] = match.sourcepos1
                        row['tlpos'] = SetUncertainAttribute('none',match,'targetpos1')
                        try:
                            if match.parallelword:
                                row['poschange'] = DefinePosChange(match.sourcepos1,match.targetpos1)
                            else:
                                #If no parallel context, use 9 as value
                                row['poschange'] = 9
                        except AttributeError:
                                row['poschange'] = 9
                        row['sl_cleansentence'] = match.matchedsentence.cleanprintstring
                        row['tl_cleansentence'] = SetUncertainAttribute('',match,'parallelsentence','cleanprintstring')
                        row['sl_context'] = match.slcontextstring
                        row['tl_context'] = SetUncertainAttribute('',match,'tlcontextstring')
                        row['slmatchid'] = match.matchedword.dbid
                        row['tlmatchid'] = SetUncertainAttribute(0,match,'parallelword','dbid')
                        row['sl_hasneg'] = match.matchedclause.hasneg
                        row['tl_hasneg'] = SetUncertainAttribute(0,match,'parallelclause','hasneg')
                        row['text_id'] = match.sourcetextid
                        row['author'] = metadata['author']
                        row['work'] = metadata['origtitle']
                        row['origyear'] = metadata['origyear']
                        row['transyear'] = metadata['transyear']
                        row['translator'] = metadata['translator']
                        row['headlemma'] = SetUncertainAttribute('',match,'headword','lemma')
                        row['matchlemma'] = match.matchedword.lemma
                        #---------------------------------------------------------
                        firstwordofcurrent = FirstLemmaOfCurrentClause(match.matchedsentence,match.matchedword)
                        firstwordofnext = FirstLemmaOfNextClause(match.matchedsentence,match.matchedword)
                        if not firstwordofnext:
                            firstposofnext = None
                            firstlemmaofnext = None
                        else:
                            firstposofnext = firstwordofnext.pos
                            firstlemmaofnext = firstwordofnext.lemma
                        row['sl_firstlemmaofthisclause'] = firstwordofcurrent.lemma
                        row['sl_firstlemmaofnextclause'] = firstlemmaofnext
                        row['sl_firstposofthisclause'] = firstwordofcurrent.pos
                        row['sl_firstposofnextclause'] = firstposofnext
                        row['sl_inversion'] = IsThisInverted2(match.matchedword,match.matchedsentence)
                        row['sl_matchcase'] = DefineCase(match.matchedword,sl)
                        row['sl_morphinfo'] = DefineMorphology(match.matchedword,sl)
                        row['sl_coordcombined'] = match.matchedclause.MarkIfCombinedCoord(match.positionmatchword)
                        row['sl_headfeat'] = SetUncertainAttribute('',match.positionmatchword,'headword','feat')
                        row['sl_deplemmas'] = match.matchedword.dependentlemmas
                        try:
                            row['sl_prevlemma'] = match.matchedclause.words_orig[match.positionmatchword.tokenid-1].lemma
                        except KeyError:
                            row['sl_prevlemma'] = None
                        row['sl_matchfeat'] = match.matchedword.feat
                        if match.parallelword:
                            firstwordofcurrent = FirstLemmaOfCurrentClause(match.parallelsentence, match.parallelword)
                            firstwordofnext = FirstLemmaOfNextClause(match.parallelsentence, match.parallelword)
                            if not firstwordofnext:
                                firstposofnext = None
                                firstlemmaofnext = None
                            else:
                                firstposofnext = firstwordofnext.pos
                                firstlemmaofnext = firstwordofnext.lemma
                            row['tl_firstlemmaofthisclause'] = firstwordofcurrent.lemma
                            row['tl_firstlemmaofnextclause'] = firstlemmaofnext
                            row['tl_firstposofthisclause'] = firstwordofcurrent.pos
                            row['tl_firstposofnextclause'] = firstposofnext
                            row['tl_inversion'] = IsThisInverted2(match.parallelword,match.parallelsentence)
                            row['tl_matchcase'] = DefineCase(match.parallelword,tl)
                            row['tl_morphinfo'] = DefineMorphology(match.parallelword,tl)
                            row['tl_coordcombined'] = match.parallelclause.MarkIfCombinedCoord(match.parallel_positionword)
                            row['tl_headfeat'] = SetUncertainAttribute('',match.parallel_positionword,'headword','feat')
                            row['tl_deplemmas'] = match.parallelword.dependentlemmas
                            try:
                                row['tl_prevlemma'] = match.parallelclause.words_orig[match.parallel_positionword.tokenid-1].lemma
                            except KeyError:
                                row['tl_prevlemma'] = None
                            row['tl_matchfeat'] = match.parallelword.feat
                        else:
                            row['tl_firstlemmaofthisclause'] = None
                            row['tl_firstlemmaofnextclause'] = None
                            row['tl_firstposofthisclause'] = None
                            row['tl_firstposofnextclause'] = None
                            row['tl_inversion'] = None
                            row['tl_matchcase'] = None
                            row['tl_morphinfo'] = None
                        #---- Some more complicated values:
                        match.DistanceInformation()
                        #
                        row['codeps_between_match_and_head'] = match.codeps_before_match_and_head
                        row['codeps_before_match_and_head']  = match.codeps_after_head_and_match
                        row['codeps_between_head_and_match'] = match.codeps_between_head_and_match
                        row['codeps_after_head_and_match']   = match.codeps_after_head_and_match
                        row['all_codeps']   = match.all_codeps
                        #
                        row = AssignDoubleLanguageValue(row,'verbdist',match.verbdist_byword)
                        row = AssignDoubleLanguageValue(row,'verbdist',match.headdist_bydependents)
                        row = AssignDoubleLanguageValue(row,'contpos',match.contpos)
                        #---------------------------------------------
                        rowlist.append(row)
                        #Information about deprels to separate tables:
                        if sl == 'ru':
                            pass
                            #row_ru_deprels['linkwordid'] = match.matchedword.dbid
                            #row_ru_deprels = ListSisters(match.positionmatchword,match.matchedclause,'ru',row_ru_deprels)
                            #rowlist_ru_deprels.append(row_ru_deprels)
                    else:
                        errorcount += 1
                    inscount += 1
                    bar.next()

                    #INSERTION:
                    if inscount / 5000 == 1:
                        print('\nInserting to table {}, this might take a while...'.format(tablename))
                        con.BatchInsert(tablename, rowlist)
                        print('Inserted {} rows.'.format(con.cur.rowcount))
                        rowlist = list()
                        rowlist_ru_deprels = list()
                        rowlist_fi_deprels = list()
                        errorcount=0
                        inscount = 0

        print('\nInserting to table {}, this might take a while...'.format(tablename))
        con.BatchInsert(tablename, rowlist)
        print('Inserted {} rows.'.format(con.cur.rowcount))

        if sl == 'ru':
            pass
            #print('\nInserting deprels for the russian sentences... '.format(errorcount))
            #con.BatchInsert('ru_deprels',rowlist_ru_deprels)
            #print('Done. Inserted {} rows.'.format(con.cur.rowcount))
        
class Match:
    """ 
    A match object contains ifromation about a concrete token that 
    is the reason for a specific match to be registered.
    """
    # A list containing the ids of all the matches found
    def __init__(self,alignsegment,matchid,sentence_id,align_id=None):
        """
        Creates a match object.
        Variables:
        -----------
        alignsegment = the segment the matching sentence is a part of
        matchid = the tokenid ('how manyth word/punct in the sentence?') of the word  that matched
        """
        #import random;x= mySearch.matches[random.choice(list(mySearch.matches.keys()))][0]
        #self.text_id = text_id
        self.context = alignsegment
        self.matchedsentence = alignsegment[sentence_id]
        self.matchedword = alignsegment[sentence_id].words[matchid]
        self.sourcetextid = self.matchedword.sourcetextid
        #For post processing purposes
        self.postprocessed = False
        self.rejectreason = ''
        self.align_id = align_id

    def postprocess(self,rejectreason):
        """If the user wants to filter the matches and mark some of them manually as accepted and some rejected"""
        self.postprocessed = True
        self.rejectreason = rejectreason

    def BuildSlContext(self,nolargecontext=False):
        """Build clause and sentence strings and object for the actual match"""
        self.slcontextstring = ''
        if nolargecontext:
            #For non-aligned data without a larger unit for context
            self.matchedclause = Clause(self.matchedsentence, self.matchedword)
            self.matchedword.ListDependents(self.matchedsentence)
            self.matchedsentence.BuildHighlightedPrintString(self.matchedword)
        else:
            #For standard, aligned data
            for sentence_id in sorted(map(int,self.context)):
                sentence = self.context[sentence_id]
                #Create a clause object for the clause containing the matched word
                self.matchedclause = Clause(self.matchedsentence, self.matchedword)
                #List the word's dependents for future use
                self.matchedword.ListDependents(self.matchedsentence)
                if sentence_id == self.matchedsentence.sentence_id:
                    sentence.BuildHighlightedPrintString(self.matchedword)
                else:
                    sentence.buildPrintString()
                self.slcontextstring += sentence.printstring + ' '
            self.slcontextstring.strip()

    def BuildTlContext(self):
        self.tlcontextstring = ''
        for sentence_id in sorted(map(int,self.parallelcontext)):
            sentence = self.parallelcontext[sentence_id]
            sentence.buildPrintString()
            self.tlcontextstring += sentence.printstring + ' '
        self.tlcontextstring.strip()

    def BuildContextString(self, nolargecontext=False):
        """Build a string containing all the sentences int the align unit the match is found in"""
        self.BuildSlContext(nolargecontext)
        #If a parallel context exists, do the same:
        try:
            if self.parallelword:
                #Create a clause object for the clause containing the parallel word
                self.parallelclause = Clause(self.parallelsentence, self.parallelword)
                #List the word's dependents for future use
                self.parallelword.ListDependents(self.parallelsentence)
                for sentence_id, sentence in self.parallelcontext.items():
                    if sentence_id == self.parallelsentence.sentence_id:
                        sentence.BuildHighlightedPrintString(self.parallelword)
                    else:
                        sentence.buildPrintString()
                    self.tlcontextstring += sentence.printstring
            else:
                #if no parallel context, leave empty
                self.tlcontextstring = ''
        except AttributeError:
            self.tlcontextstring = ''


    def BuildSentencePrintString(self):
        """Constructs a printable sentence and highliths the match
        """
        self.matchedsentence.BuildHighlightedPrintString(self.matchedword)

    def CatchHead(self):
        """Store the matches head in a separate object,if possible. If not, return the sentence's id"""
        try:
            self.headword = self.matchedsentence.words[self.matchedword.head]
            self.matchedword.headword = self.matchedsentence.words[self.matchedword.head]
            try:
                #try to define the head of the head
                self.headshead = self.matchedsentence.words[self.headword.head]
            except KeyError:
                self.headshead = None
        except KeyError:
            self.headword = None
            self.matchedword.headword = None
            return False

        #For parallel contexts: ================================================

        try:
            if self.parallelword:
                #if there is a parallel context
                try:
                    self.parallel_headword = self.parallelsentence.words[self.parallelword.head]
                    self.parallelword.headword = self.parallelsentence.words[self.parallelword.head]
                    try:
                        #try to define the head of the head
                        self.parallel_headshead = self.parallelsentence.words[self.parallel_headword.head]
                    except KeyError:
                        self.parallel_headshead = None
                except KeyError:
                    self.parallel_headword = None
                    self.parallelword.headword = None
        except AttributeError:
            self.parallelword = None
            self.parallelcontext = None


        # If headword (for the source context) succesfully defined, return true
        return True

    def LocateTargetWord(self, search):
        """ask the user to locate the target work in the match and mark it in the database / search object
        The goal here is to give values to 3 attributes of the match:
        ============================
        - parallelcontext (already given)
        - parallelsentence
        - parallelword
        """
        self.parallelsentence = None
        self.parallelword = None
        #1. Reorder the sentences i the parlallel segment
        parallel_sentence_ids = self.SortTargetSentences()
        #2. Iterate over the paralallel sentences: 
        if not self.EvaluateTargetSentences(parallel_sentence_ids,search):
            #If no direct match, decide which sentence in the target segment matches the closest
            self.parallelsentence = self.PickTargetSentence()
            if self.PickTargetWord():
                #Add or don't add the picked word to possible translations if the user picked a word
                addmenu = multimenu({'y':'yes','n':'no'}, 'Should {} be added as another possinle translation for {}?'.format(self.parallelword.lemma, self.matchedword.lemma))
                if addmenu.answer == 'y':
                    search.matchlemmas[self.matchedword.lemma].append(self.parallelword.lemma)
        #Mark this aligned
        self.aligned = True

    def SortTargetSentences(self):
        #First, find out how manyth sentence the matched word is located in in the source language:
        sentence_in_segment = list(self.context.keys()).index(self.matchedsentence.sentence_id)
        #Then, first try the sameth element in the tl segment's sentences
        parallel_sentence_ids = list(self.parallelcontext.keys())
        try:
            match_sentence_id = parallel_sentence_ids[sentence_in_segment]
        except (KeyError, IndexError):
            #If there are less sentences in the target, start with the first sentence
            match_sentence_id = parallel_sentence_ids[0]
        #Reorder the parallel sentences so that the one that is the sameth as in the match will by tried first
        parallel_sentence_ids_reordered = [match_sentence_id]
        for psid in parallel_sentence_ids:
            if psid != match_sentence_id:
                parallel_sentence_ids_reordered.append(psid)
        return parallel_sentence_ids_reordered

    def EvaluateTargetSentences(self, parallel_sentence_ids, search):
        """Iterate over the sentences that have a word speficied as a possible translation"""
        #Initialize menus etc
        self.BuildSentencePrintString()
        parmenu = multimenu({'y':'yes','n':'no','s':'syntactically dissimilar','d':'delete segment as untemporal after all'})
        parmenu.clearscreen = False
        parmenu.question = 'Is this the correct matching word?'
        #Loop:
        for matchlemma in search.matchlemmas[self.matchedword.lemma]:
            #In a fixed order, check whether this word's lemma is listed as a possible translation
            for sentence_id in parallel_sentence_ids:
                sentence = self.parallelcontext[sentence_id]
                for tokenid, word in sentence.words.items():
                    #iterate over words in this sentence
                    if word.lemma == matchlemma:
                        sentence.BuildPrintString(word.tokenid)
                        #Clear terminal output:
                        os.system('cls' if os.name == 'nt' else 'clear')
                        print('\n'*15)
                        sentence.PrintTargetSuggestion(self.matchedsentence.printstring)
                        if parmenu.prompt_valid() == 'y':
                            #save the information about the target word/sentence
                            self.parallelsentence = sentence
                            self.parallelword = word
                            return True
                        elif parmenu.answer =='s':
                            self.parallelsentence = sentence
                            self.parallelword = None
                            return True
                        elif parmenu.answer =='d':
                            self.postprocess('Rejected as non-temporal')
                            return True
        #If nothing was accepted, return false
        return False

    def PickTargetSentence(self):
        """Prints out a menu of all the target sentences"""
        #if nothing was found or nothing was an actual match
        sentencemenu = multimenu({})
        sentencemenu.clearscreen = False
        sid = 1
        #Clear terminal output:
        os.system('cls' if os.name == 'nt' else 'clear')
        for sentence_id, sentence in self.parallelcontext.items():
            #print all the alternatives again:
            sentence.BuildPrintString()
            print('{}:{}'.format(sid,sentence_id))
            sentence.PrintTargetSuggestion(self.matchedsentence.printstring)
            sentencemenu.validanswers[str(sid)] = sentence_id
            sid += 1
            if sid % 6 == 0:
                input('Long list of sentences, more to follow...')
        sentencemenu.prompt_valid('Which sentence is the closest match to the source sentence?')
        #return the answer:
        return self.parallelcontext[int(sentencemenu.validanswers[sentencemenu.answer])]

    def PickTargetWord(self):
        """Picks a word from the selected target sentence as the closest match (or picks none)"""
        wordmenu = multimenu({})
        wordmenu.clearscreen = False
        for tokenid, word in self.parallelsentence.words.items():
            if word.token not in string.punctuation:
                wordmenu.validanswers[str(tokenid)] = word.token
        wordmenu.validanswers['999'] = 'None'
        wordmenu.validanswers['9999'] = 'Reject match'
        wordmenu.cancel = 'No single word can be specified'
        wordmenu.prompt_valid('Wich word is the closest match to {}?'.format(self.matchedword.token))
        if int(wordmenu.answer) < 999:
            #SET the parallel word:
            self.parallelword = self.parallelsentence.words[int(wordmenu.answer)]
            return True
            #######
        elif wordmenu.answer == '9999':
            self.postprocess('Rejected as non-temporal')
            return False
        elif wordmenu.answer == '999':
            return False

    def DefinePositionMatch(self):
        """Define what part of the match is the direct  dependent of a verb etc"""
        try:
            self.positionmatchword = self.matchedword
            #Check the words head
            self.CatchHead()
            #Do it in a better way (leaving the above for compatibility's sake):
            self.positionmatchword.CatchHead(self.matchedsentence)
            if self.headword.pos in ('S') or self.headword.token in ('aikana','välein'):
                #if the match is actually a dependent of a pronoun (or the Finnish 'aikana')
                # LIST all the other possible cases as well!
                self.positionmatchword = self.headword
            elif self.headshead:
                if self.headshead.pos in ('S') and self.headword.pos != 'V':
                    #or if the match's head  is actually a dependent of a pronoun (AND the match's head is not a verb)
                    self.positionmatchword = self.headshead
            try:
                self.headword = self.matchedsentence.words[self.positionmatchword.head]
            except KeyError:
                #FOR SN idiotism...
                self.headword = None

            # =========================================================================0

            if self.parallelword:
                #If there is a comparable parallel context
                self.parallel_positionword = self.parallelword
                if self.parallel_headword.pos in ('S') or self.parallel_headword.token in ('aikana','välein'):
                    #if the match is actually a dependent of a pronoun
                    self.parallel_positionword = self.parallel_headword
                elif self.parallel_headshead:
                    if self.parallel_headshead.pos in ('S') and self.parallel_headword.pos != 'V':
                        #or if the match's head  is actually a dependent of a pronoun
                        self.parallel_positionword = self.parallel_headshead
                #set the head for the position word
                try:
                    self.parallel_headword = self.parallelsentence.words[self.parallel_positionword.head]
                    #Do it in a better way (leaving the above for compatibility's sake):
                    self.parallel_positionword.CatchHead(self.parallelsentence)
                except KeyError:
                    #FOR SN idiotism...
                    self.parallel_headword = None

            #If no errors, return true
            return True

        except AttributeError:
            #If something wrong, return false
            return False
        except KeyError:
            #If something wrong, return false
            return False

    def DefinePosition1(self):
        """Define, whether the match is located clause-initially, clause-finally or in the middle"""
        #if self.matchedword.dbid ==  166728:
        #import ipdb; ipdb.set_trace()
        if self.DefinePositionMatch():
            #list the words dependents
            self.positionmatchword.ListDependentsRecursive(self.matchedsentence)
            #For the source segment
            if IsThisClauseInitial(self.positionmatchword, self.matchedsentence):
                self.sourcepos1 = 'clause-initial'
            elif IsThisClauseFinal(self.positionmatchword, self.matchedsentence, self.matchedword):
                self.sourcepos1 = 'clause-final'
            else:
                self.sourcepos1 = 'middle'
            #For the target segment
            if self.parallelword:
                #list the words dependents
                self.parallel_positionword.ListDependentsRecursive(self.parallelsentence)
                if IsThisClauseInitial(self.parallel_positionword, self.parallelsentence):
                    self.targetpos1 = 'clause-initial'
                elif IsThisClauseFinal(self.parallel_positionword, self.parallelsentence, self.parallelword):
                    self.targetpos1 = 'clause-final'
                else:
                    self.targetpos1 = 'middle'
            return True
        else:
            return False

    def DistanceInformation(self):
        """Calculate distances between elements in the clause of the match"""
        #self.DefinePosition1()
        #self.BuildContextString()
        #-----
        languages = [{'word':self.positionmatchword,'clause':self.matchedclause,'lname':'sl'}]
        self.verbdist_byword = dict()
        self.headdist_bydependents = dict()
        self.contpos = dict()
        if self.parallelcontext:
            #if there is a parallel context, analyze that, too
            try:
                languages.append({'word':self.parallel_positionword,'clause':self.parallelclause,'lname':'tl'})
            except AttributeError:
                pass
        for language in languages:
            if language['clause'].FirstFiniteVerb():
                #1.1: distance between the first finite verb and the posmatch
                #Note: -1 from the result of the defining function
                try:
                    self.verbdist_byword[language['lname']] = language['clause'].DefineDistanceFromFiniteVerb(language['word']) - 1 
                except TypeError:
                    import ipdb; ipdb.set_trace()
            if language['word'].CatchHead(self.matchedsentence):
                #1.2: how many dependents of the same level are there between the word and its head
                distance = language['clause'].DefineDistanceOfCodependents(language['word'])
                self.headdist_bydependents[language['lname']] = distance
                #1.3. What is the distance from the head word both backwards and forwards
                #notice, that 0 is not an option here, so adding or subtracting 1
                distance_b = distance
                if language['clause'].matchbeforehead:
                    distance = 0 - distance -1
                else:
                    distance = distance + 1

                self.contpos[language['lname']] = distance

        #Not yet muoltilingual!
        try:
            self.codeps_between_match_and_head = self.positionmatchword.codeps_between_match_and_head 
            self.codeps_before_match_and_head  = self.positionmatchword.codeps_before_match_and_head 

            self.codeps_between_head_and_match = self.positionmatchword.codeps_between_head_and_match
            self.codeps_after_head_and_match   = self.positionmatchword.codeps_after_head_and_match  
            self.all_codeps   = self.positionmatchword.all_codeps
        except AttributeError:
            print('.')
            self.codeps_between_match_and_head = ''
            self.codeps_before_match_and_head  = ''

            self.codeps_between_head_and_match = ''
            self.codeps_after_head_and_match   = ''
            self.all_codeps   = ''

        return True

class MonoMatch(Match):

    def __init__(self,matchid,sentence):
        """
        Creates a MONOLINGUAL match object.
        Variables:
        -----------
        matchid = the tokenid ('how manyth word/punct in the sentence?') of the word  that matched
        """
        #import random;x= mySearch.matches[random.choice(list(mySearch.matches.keys()))][0]
        #self.text_id = text_id
        self.matchedsentence = sentence
        self.matchedword = sentence.words[matchid]
        self.sourcetextid = self.matchedword.sourcetextid
        #For post processing purposes
        self.postprocessed = False

class Sentence:
    """
    The sentence consists of words (which can actually also be punctuation marks).
    The words are listed in a dictionary. The words tokenid (it's ordinal place in the sentence) 
    is the key in the dictionary of words.
    """
    def __init__(self,sentence_id):
        self.sentence_id = sentence_id
        #initialize a dict of words. The word's ids in the sentence will be used as keys
        self.words = dict()
        #By default, the sentence's matchids attribute is an empty list = no matches in this sentence
        self.matchids = list()

    def BuildHighlightedPrintString(self,matchedword):
        """Constructs a printable sentence and highliths the match
        """
        self.printstring = ''
        #create an string also without the higlight
        self.cleanprintstring = ''
        self.colorprintstring = ''
        self.Headhlprintstring = ''
        isqmark = False
        for idx in sorted(self.words.keys()):
            spacechar = ' '
            word = self.words[idx]
            try:
                previous_word = self.words[idx-1]
                #if previous tag is a word:
                if previous_word.pos != 'Punct' and previous_word.token not in string.punctuation:
                    #...and the current tag is a punctuation mark. Notice that exception is made for hyphens, since in mustikka they are often used as dashes
                    if word.token in string.punctuation and word.token != '-':
                        #..don't insert whitespace
                        spacechar = ''
                        #except if this is the first quotation mark
                        if word.token == '\"' and not isqmark:
                            isqmark = True
                            spacechar = ' '
                        elif word.token == '\"' and isqmark:
                            isqmark = False
                            spacechar = ''
                #if previous tag was not a word
                elif previous_word.token in string.punctuation:
                    #...and this tag is a punctuation mark
                    if (word.token in string.punctuation and word.token != '-' and word.token != '\"') or isqmark:
                        #..don't insert whitespace
                        spacechar = ''
                    if previous_word.token == '\"':
                        spacechar = ''
                        isqmark = True
                    else:
                        spacechar = ' '
            except:
                #if this is the first word
                spacechar = ''
            #if this word is a match:
            if word.tokenid == matchedword.tokenid:
                #Surround the match with <>
                self.printstring += spacechar + '<' + word.token  + '>'
                self.Headhlprintstring += spacechar + '<<' + word.token  + '>>Y'
                self.colorprintstring += spacechar + bcolors.GREEN + word.token + bcolors.ENDC 
            elif word.tokenid == matchedword.head:
                self.Headhlprintstring += spacechar + '<' + word.token  + '>X'
                self.printstring += spacechar + word.token
                self.colorprintstring += spacechar + word.token
            else:
                self.printstring += spacechar + word.token
                self.colorprintstring += spacechar + word.token
                self.Headhlprintstring += spacechar + word.token
            self.cleanprintstring += spacechar + word.token

    def buildPrintString(self):
        """Constructs a printable sentence"""
        self.printstring = ''
        isqmark = False
        for idx in sorted(self.words.keys()):
            spacechar = ' '
            word = self.words[idx]
            try:
                previous_word = self.words[idx-1]
                #if previous tag is a word:
                if previous_word.pos != 'Punct' and previous_word.token not in string.punctuation:
                    #...and the current tag is a punctuation mark. Notice that exception is made for hyphens, since in mustikka they are often used as dashes
                    if word.token in string.punctuation and word.token != '-':
                        #..don't insert whitespace
                        spacechar = ''
                        #except if this is the first quotation mark
                        if word.token == '\"' and not isqmark:
                            isqmark = True
                            spacechar = ' '
                        elif word.token == '\"' and isqmark:
                            isqmark = False
                            spacechar = ''
                #if previous tag was not a word
                elif previous_word.token in string.punctuation:
                    #...and this tag is a punctuation mark
                    if (word.token in string.punctuation and word.token != '-' and word.token != '\"') or isqmark:
                        #..don't insert whitespace
                        spacechar = ''
                    if previous_word.token == '\"':
                        spacechar = ''
                        isqmark = True
                    else:
                        spacechar = ' '
            except:
                #if this is the first word
                spacechar = ''
            #if this word is a match:
            try:
                if word.tokenid in self.matchids:
                    self.printstring += spacechar + '*' + word.token  + '*'
                else:
                    self.printstring += spacechar + word.token
            except AttributeError:
                self.printstring += spacechar + word.token

    def buildStringToVisualize(self):
        """Build a string to be saved in a file to be run through the TDT visualizer"""
        csvrows = list()
        for idx in sorted(self.words.keys()):
            word = self.words[idx]
            csvrows.append([word.tokenid,word.token,word.lemma,word.pos,word.pos,word.feat,word.feat,word.head,word.head,word.deprel,word.deprel,'_','_'])
        self.visualizable = csvrows

    def visualize(self):
        """Make a file and visualize it"""
        with open('input.conll9','w') as f:
            writer = csv.writer(f, delimiter='\t')
            writer.writerows(self.visualizable)
        os.system("cat input.conll9 | python /home/juho/Dropbox/VK/skriptit/python/finnish_dep_parser/Finnish-dep-parser/visualize.py > output.html")

    def texvisualize(self,lang):
        """Visualize with tikz/latex"""
        #set latex encoding
        if lang == 'finnish':
            enc = "T1"
        elif lang == 'russian':
            enc = "T2A"
        preamp = """\\documentclass[{0}]{{standalone}}
            \\usepackage{{tikz-dependency}}
            \\usepackage[utf8]{{inputenc}}
            \\usepackage[{1}]{{fontenc}}
            \\usepackage[{0}]{{babel}}
            \\begin{{document}}
            \\begin{{dependency}}[theme = simple]""".format(lang,enc)
        deptext = "\n\\begin{deptext}[column sep=1em]\n"
        texend = """
            \\end{dependency}
            \\end{document}"""
        deprels = ""
        #in case of messed up russian sentences:
        numbercompensation = 0
        firstword=True
        for wkey in sorted(map(int,self.words)):
            word = self.words[wkey]
            tokenid = int(word.tokenid)
            head = int(word.head)
            if firstword:
                numbercompensation = tokenid - 1
                firstword = False
            #test if the token ids don't start at 1
            head -= numbercompensation
            tokenid -= numbercompensation
            if wkey < len(self.words):
                deptext +=  word.token + " \\& "
            else:
                deptext +=  word.token + " \\\\"
            if word.deprel == 'ROOT':
                deprels += "\n\\deproot{{{}}}{{ROOT}}".format(tokenid)
            else:
                deprels += "\n\\depedge{{{0}}}{{{1}}}{{{2}}}".format(head,tokenid,word.deprel)
        deptext += "\n\\end{deptext}\n"
        with open('{}_{}.tex'.format(lang,self.sentence_id),mode="w", encoding="utf8") as f:
            f.write('{}{}{}{}\n'.format(preamp,deptext,deprels,texend))

    def listDependents(self, mtokenid):
        """return a list of dependents of the specified word"""
        dependents = list()
        self.dependentDict = dict()
        self.dependentDict_prints = dict()
        for tokenid, word in self.words.items():
            if word.head == mtokenid:
                dependents.append(word)
                #This is for building command line questions concerning the dependents
                self.dependentDict[str(tokenid)] = word
                self.dependentDict_prints[str(tokenid)] = word.token
        self.dependentlist = dependents


    def FirstWordOfCurrentClause(self, currentword):
        """Return the tokenid of the first word of the clause specified by a word"""
        self.tokenids = sorted(map(int,self.words))
        this_tokenid = currentword.tokenid
        while not FirstWordOfClause(self, self.words[this_tokenid]) and this_tokenid > min(self.tokenids):
            this_tokenid -= 1
            if this_tokenid == min(self.tokenids):
                # if this is the first word of the whole sentence
                break
        return this_tokenid

    def LastWordOfCurrentClause(self, currentword):
        """Return the last word of the clause specified by a word"""
        self.tokenids = sorted(map(int,self.words))
        this_tokenid = currentword.tokenid
        #Move forward from the current word to reach either end of sentence or a marker for the beginning of a new clause
        #How to deal with relative clauses in the middle of a sentence?
        while not FirstWordOfClause(self, self.words[this_tokenid]) and this_tokenid < max(self.tokenids):
            this_tokenid += 1
            if this_tokenid == max(self.tokenids):
                # if this is the last word of the whole sentence
                return this_tokenid
        #If a marker for the next clause was met, assume that the previous word was the last of the current clause:
        return this_tokenid - 1

class Clause(Sentence):
    """An attemp to separate clauses from sentences"""
    def __init__(self, sentence, word):
        first_tokenid = sentence.FirstWordOfCurrentClause(word)
        last_tokenid = sentence.LastWordOfCurrentClause(word)
        leftborder = sentence.tokenids.index(first_tokenid)
        rightborder = sentence.tokenids.index(last_tokenid)+1
        self.words = dict()
        self.words_orig = dict()
        self.deprels = list()
        word_idx = 1
        clause_tokenids = sentence.tokenids[leftborder:rightborder]
        for tokenid in clause_tokenids:
            self.words[word_idx] = sentence.words[tokenid]
            self.words_orig[sentence.words[tokenid].tokenid] = sentence.words[tokenid]
            self.deprels.append(sentence.words[tokenid].deprel)
            word_idx += 1
        self.BuildHighlightedPrintString(word)
        self.HasNeg()
        self.FirstFiniteVerb()

    def HasNeg(self):
        neglemmas = ('не','нет','ei')
        self.hasneg = 0
        for tokenid, word in self.words.items():
            if word.lemma in neglemmas:
                self.hasneg = 1
                break

    def FirstFiniteVerb(self):
        """Get the tokenid of the first finite ver in the clause"""
        for tokenid in sorted(map(int,self.words)):
            if self.words[tokenid].IsThisFiniteVerb():
                self.finiteverbid = self.words[tokenid].tokenid
                return True
        #If no finite verb, return False
        self.finiteverbid = None
        return False

    def DefineDistanceFromFiniteVerb(self,mword):
        """Return the distance between a word and the first finite verb of the clause"""
        #if mword.dbid == 442568:
        #    import ipdb; ipdb.set_trace()
        if mword.tokenid > self.finiteverbid:
            after_finite = True
        elif mword.tokenid < self.finiteverbid:
            after_finite = False
        phraseborder = mword.tokenid
        if mword.ListDependents(self):
            #If there are depentendts of the posmatch, get the furthest right/left dependent
            for dep in mword.dependentlist:
                if dep.tokenid != self.finiteverbid:
                    #avoid weird cases where verb depends on the adverbial
                    if after_finite:
                        if dep.tokenid < phraseborder:
                            phraseborder = dep.tokenid
                    else:
                        if dep.tokenid > phraseborder:
                            phraseborder = dep.tokenid
        #Save the phrase border for future reference
        mword.phraseborder = phraseborder
        #count the distances
        if phraseborder > self.finiteverbid:
            return phraseborder - self.finiteverbid
        elif phraseborder < self.finiteverbid:
            return self.finiteverbid - phraseborder

    def DefineDistanceOfCodependents(self,mword):
        """Return how many dependents of the same level there are between a word and its head"""
        mword.headword.ListDependents(self)
        codepsbetween = 0
        headid = mword.headword.tokenid 

        mword.codeps_between_match_and_head = ''
        mword.codeps_before_match_and_head  = ''
        mword.codeps_between_head_and_match = ''
        mword.codeps_after_head_and_match  = ''
        mword.all_codeps = ''

        self.codpesafter = ''
        if mword.tokenid > headid:
            self.matchbeforehead = False
            for codep in mword.headword.dependentlist:
                mword.all_codeps += '#' + codep.deprel
                if codep.tokenid > headid and codep.tokenid < mword.tokenid:
                    codepsbetween += 1

                #UPDATE deprel information about codeps:
                if codep.tokenid > headid and codep.tokenid < mword.tokenid:
                    #codeps between head and match
                    mword.codeps_between_head_and_match += '#' +  codep.deprel
                if codep.tokenid > headid and codep.tokenid > mword.tokenid:
                    #codeps between head and match
                    mword.codeps_after_head_and_match +=  '#' + codep.deprel

        elif mword.tokenid < headid:
            self.matchbeforehead = True
            for codep in mword.headword.dependentlist:
                mword.all_codeps += '#' + codep.deprel
                if codep.tokenid < headid and codep.tokenid > mword.tokenid:
                    codepsbetween += 1
                #UPDATE deprel information about codeps:
                if codep.tokenid < headid and codep.tokenid > mword.tokenid:
                    #codeps between head and match
                    mword.codeps_between_match_and_head += '#' + codep.deprel
                if codep.tokenid < headid and codep.tokenid < mword.tokenid:
                    #codeps between head and match
                    mword.codeps_before_match_and_head += '#' + codep.deprel

        return codepsbetween

    def MarkIfCombinedCoord(self, mword):
        """This method specifically for determining what counts as clause-initiality"""
        mword.DefineAdverbialPhraseBorder(self)
        try:
            wordbefore = self.words_orig[mword.phraseborder['left'] - 1]
            wordafter  = self.words_orig[mword.phraseborder['right'] + 1]
            if wordbefore.token in ('и','или','а') and wordafter.IsThisFiniteVerb():
                return 1
        except KeyError:
            pass
        #If no condition matches, return 0
        return 0

class TargetSentence(Sentence):
    """This is specially for the sentences in the parallel context. The main difference from 
    original sentences is that match"""
    def __init__(self, sentence_id):
        self.sentence_id = sentence_id
        #initialize a dict of words. The word's ids in the sentence will be used as keys
        self.words = dict()
        #By default, the sentence's matchids attribute is an empty list = no matches in this sentence
        self.targetword = None

    def BuildPrintString(self, candidateid=0):
        """Constructs a printable sentence and highliths the candidate for target match
        """
        self.printstring = ''
        self.colorprintstring = ''
        #create an string also without the higlight
        self.cleanprintstring = ''
        isqmark = False
        for idx in sorted(self.words.keys()):
            spacechar = ' '
            word = self.words[idx]
            try:
                previous_word = self.words[idx-1]
                #if previous tag is a word:
                if previous_word.pos != 'Punct' and previous_word.token not in string.punctuation:
                    #...and the current tag is a punctuation mark. Notice that exception is made for hyphens, since in mustikka they are often used as dashes
                    if word.token in string.punctuation and word.token != '-':
                        #..don't insert whitespace
                        spacechar = ''
                        #except if this is the first quotation mark
                        if word.token == '\"' and not isqmark:
                            isqmark = True
                            spacechar = ' '
                        elif word.token == '\"' and isqmark:
                            isqmark = False
                            spacechar = ''
                #if previous tag was not a word
                elif previous_word.token in string.punctuation:
                    #...and this tag is a punctuation mark
                    if (word.token in string.punctuation and word.token != '-' and word.token != '\"') or isqmark:
                        #..don't insert whitespace
                        spacechar = ''
                    if previous_word.token == '\"':
                        spacechar = ''
                        isqmark = True
                    else:
                        spacechar = ' '
            except:
                #if this is the first word
                spacechar = ''
            #if this word is the target candidate
            if word.tokenid == candidateid:
                #paint the possible target word red
                self.colorprintstring += spacechar + bcolors.RED + word.token + bcolors.ENDC
                self.printstring += spacechar + '<<' + word.token  + '>>'
            else:
                self.printstring += spacechar + word.token
                self.colorprintstring += spacechar + word.token
            self.cleanprintstring += spacechar + word.token
            if candidateid == 0:
                self.printstring = self.cleanprintstring
                self.colorprintstring = self.cleanprintstring

    def PrintTargetSuggestion(self, sourcecontext):
        """Print, for the user to compare, a context:"""
        #Initialize table printer
        table = Texttable()
        table.set_cols_align(["l", "l"])
        table.set_cols_valign(["m", "m"])
        table.add_rows([['Original sentence','proposed sentence in the TL segment'],[get_color_string(bcolors.BLUE,sourcecontext), get_color_string(bcolors.RED,self.printstring)]])
        #print the suggestion as a table
        print(table.draw() + "\n")

    def SetTargetWord(self,tokenid):
        """Sets the target word"""
        #save the information in the database
        #con = psycopg(parentSearch.queried_db,'juho')
        #con.query('UPDATE {} SET tr_did = %(tr_dbid)s WHERE id = %(this_id)s'.format(parentSearch.queried_table),{'tr_dbid':targetword.dbid,'this_id':sourceword.dbid})
        self.targetword = tokenid
        
class Word:
    """A word object containing all the morhpological and syntactic information"""
    def __init__(self,row):
        #Initialize all properties according to information from the database
        self.token = row["token"]
        self.lemma = row["lemma"]
        self.pos = row["pos"]
        self.feat = row["feat"]
        self.head = row["head"]
        self.deprel = row["deprel"] 
        self.tokenid = row["tokenid"] 
        self.sourcetextid = row["text_id"]
        #The general id in the db conll table
        self.dbid =  row["id"]

    def printAttributes(self):
        print('Attributes of the word:\n token = {} \n lemma = {} \n feat = {} \n  pos = {}'.format(self.token,self.lemma,self.feat,self.pos))

    def ListDependents(self, sentence):
        """return a list of dependents of the specified word"""
        dependents = list()
        #For sepcial use in collecting data for analysis:
        self.dependentlemmas = ''
        self.dep_positions = dict()
        for tokenid, word in sentence.words.items():
            if word.head == self.tokenid:
                dependents.append(word)
                self.dependentlemmas += word.lemma + '#'
                #self.dep_positions[word.deprel].append(tokenid)
                #self.dependentlemmas_ordered += '[{}]'.format() = tokenid
        self.dependentlist = dependents
        #If there were'nt any dependents, return false
        return dependents

    def HasHead(self,sentence):
        self.hashead = True
        for tokenid, word in sentence.words.items():
            if word.tokenid == self.head:
                self.hashead = False

    def ListDependentsRecursive(self, sentence):
        """return a recursive list of dependents of the specified word"""
        self.ListDependents(sentence)
        self.rdeplist = defaultdict(list)
        for dep1 in self.dependentlist:
            #The direct dependents of the word
            self.rdeplist[dep1.tokenid] = dep1
            dep1.ListDependents(sentence)
            for dep2 in dep1.dependentlist:
                #The dependents of the dependents of the word
                self.rdeplist[dep2.tokenid] = dep2
                dep2.ListDependents(sentence)
                for dep3 in dep2.dependentlist:
                    #The dependents of the dependents of the dependents of the word
                    self.rdeplist[dep3.tokenid] = dep3
                    dep3.ListDependents(sentence)
                    for dep4 in dep3.dependentlist:
                        #The dependents of the dependents of the....
                        self.rdeplist[dep4.tokenid] = dep4
                        dep4.ListDependents(sentence)

    def CatchHead(self, sentence):
        """Store the words head in a separate object,if possible."""
        try:
            self.headword = sentence.words[self.head]
        except KeyError:
            self.headword = None
            return False

        # If headword succesfully defined, return true
        return True

    def DefineAdverbialPhraseBorder(self,clause):
        """Return the distance between a word and the first finite verb of the clause"""
        self.phraseborder = dict()
        self.phraseborder['left'] = self.tokenid
        self.phraseborder['right'] = self.tokenid
        if self.ListDependents(clause):
            #If there are depentendts of the posmatch, get the furthest right/left dependent
            for dep in self.dependentlist:
                if not dep.IsThisFiniteVerb():
                    #avoid weird cases where a finite verb depends on the adverbial
                    if dep.tokenid < self.phraseborder['left']:
                        self.phraseborder['left'] = dep.tokenid
                    elif dep.tokenid > self.phraseborder['right']:
                        self.phraseborder['right'] = dep.tokenid

    def IsThisFiniteVerb(self):
        """Return true if the word object is by its feat a finite verb form"""
        if self.feat[0:3] in ('Vmi','Vmm') or ItemInString(['MOOD_Ind','MOOD_Imprt','MOOD_Pot','MOOD_Cond'],self.feat):
            return True
        else:
            return False

######################################################################

def PrintTimeInformation(elapsedtimes,start,done,matchcount,bar):
    """ Print information about the manual annotations etc"""
    #Clear terminal output:
    os.system('cls' if os.name == 'nt' else 'clear')
    elapsedtimes.append(time.time() - start)
    #Remove the longest and two shortest times
    avgtime = mean(elapsedtimes)
    timetogo = str(datetime.timedelta(seconds=(matchcount-done)*int(avgtime)))
    pace = str(int(60/avgtime*10)) + '/10 min'
    text = colored('\nTime used for the most recent: {}','red') + colored('\n\Current pace: {}', 'green') + colored('\nWith this pace you have {} left\n','blue')
    bar.next()
    print(text.format(elapsedtimes[-1],pace,timetogo))
    return elapsedtimes

def DefineHeadOfMatchPhrase(word):
    """Define what part of the match is dependent of a verb etc"""
    pass

def IsThisClauseInitial(mword, msentence):
    """Define, whether the match is located clause-initially"""
    #if mword.dbid == 166728:
    #    import ipdb; ipdb.set_trace()
    this_tokenid = msentence.FirstWordOfCurrentClause(mword)
    #2. Find out what's between the punctuation mark / conjunction / sentence border and the match
    #First, assume this IS clause-initial
    clauseinitial = True
    if mword.tokenid == max(msentence.tokenids):
        return False
    if (mword.tokenid + 1 == max(msentence.tokenids) or mword.tokenid == max(msentence.tokenids)) and msentence.words[mword.tokenid + 1].token in string.punctuation:
        #A hacky fix to prevent sentence-final items being anayzed as clause-initial
        return False
    if this_tokenid == min(msentence.tokenids):
        #If this is the first clause of the sentence
        clauseborder = 0
    else:
        clauseborder = msentence.tokenids.index(this_tokenid)+1
    matchindex = msentence.tokenids.index(mword.tokenid)
    tokenids_beforematch = msentence.tokenids[clauseborder:matchindex]
    for tokenid in tokenids_beforematch:
        #if there is a word between the bmarker and the match, assume that the match is not clause-initial 
        clauseinitial = False
        word = msentence.words[tokenid]
        if any([word.head == mword.tokenid, word.tokenid in mword.rdeplist]) and word.lemma not in ('tosin') and word.deprel not in ('cop','nsubj-cop'):
            #the  rdeplist thing helps to scan dependents pf dependents
            #except if this is a depent of the match or a conjunction.. See also the hack above for some unwanted dependents
            clauseinitial = True
        else:
            #If all the above tests fail, then assume that there is a word before the match in the clause
            break
    return clauseinitial

def IsThisClauseFinal(mword, msentence, actualmatchword):
    """Define, whether the match is located clause-initially"""
    #if mword.dbid == 531108:
    #    import ipdb; ipdb.set_trace()
    last_tokenid = msentence.LastWordOfCurrentClause(mword)
    if mword.tokenid == last_tokenid:
        # If this is the absolute final word of the clause, return true
        return True
    # If not,  find out what's between the match and a punctuation mark / conjunction / sentence border 
    matchindex = msentence.tokenids.index(mword.tokenid) + 1 
    if last_tokenid == max(msentence.tokenids):
        #If this is the last clause of the sentence
        tokenids_aftermatch = msentence.tokenids[matchindex:]
    else:
        lastwordindex = msentence.tokenids.index(last_tokenid) + 1 
        tokenids_aftermatch = msentence.tokenids[matchindex:lastwordindex]

    #First, assume this IS clause-final
    clausefinal = True
    for tokenid in tokenids_aftermatch:
        #if there is a word between the bmarker and the match, assume that the match is not clause-final 
        clausefinal = False
        word = msentence.words[tokenid]
        if word.head == mword.tokenid or word.token in string.punctuation:
            #except if this is a depent of the match or a punctuation mark
            clausefinal = True
            #Special conditions:
            if word.deprel == 'nommod' and mword.deprel == 'dobj':
                #in TDT there are errors with OSMAs, this is a try to fix some of them
                break
        elif word.token == 'назад':
            #special case: Russian nazad as the last word of clause
            if tokenid -1 == mword.tokenid:
                clausefinal = True
            else:
                #a hack for possible tomu nazad... let pjat nazad... cases:
                try:
                    prev1 = msentence.words[tokenid-1]
                    prev2 = msentence.words[tokenid-2]
                    if prev1.token in ('тому') and prev2.tokenid == mword.tokenid:
                        clausefinal = True
                    if prev1.pos in ('M','N') and prev2.tokenid == mword.tokenid:
                        clausefinal = True
                except:
                    clausefinal = False
        elif mword.pos == 'S' and tokenid > mword.tokenid and word.head != mword.tokenid:
            #special case: russian preposition that govern the match wich has its OWN dependents
            if word.head == actualmatchword.tokenid:
                clausefinal = True
        else:
            try:
                #special case: Russian "minut na sem" expressions
                plusone = msentence.words[tokenids_aftermatch[tokenid+1]]
                plustwo = msentence.words[tokenids_aftermatch[tokenid+2]]
                if plusone.lemma in ('на','в') and plustwo.pos == 'M' and tokenid+2 == max(tokenids):
                    clausefinal = True
                    break
            except IndexError:
                pass
            #If all the above tests fail, then assume that there is a word before the match in the clause
            break
        if not clausefinal:
            #If there was a word after the tested word and it didn't match any conditions, break the loop
            break
    return clausefinal

def IsThisInverted(mword, msentence):
    """examine, wthere a clause has inverted (vs) order"""
    left_border = msentence.FirstWordOfCurrentClause(mword)
    right_border = msentence.LastWordOfCurrentClause(mword)
    lb_index = msentence.tokenids.index(left_border)
    rb_index = msentence.tokenids.index(right_border)
    if rb_index < max(msentence.tokenids):
        #if this is not the last word of the sentence, include it in the clause
        rb_index += 1
    for tokenid in msentence.tokenids[lb_index:rb_index]:
        word = msentence.words[tokenid]
        if word.deprel in ('nsubj','предик'):
            subjectshead = msentence.words[word.head]
            if subjectshead.tokenid < word.tokenid and subjectshead.pos == 'V':
                return 1
    return 0

def IsThisInverted2(mword, msentence):
    """examine, wthere a clause has inverted (vs) order. Don't rely on dependency but try to find a finite verb"""
    left_border = msentence.FirstWordOfCurrentClause(mword)
    right_border = msentence.LastWordOfCurrentClause(mword)
    lb_index = msentence.tokenids.index(left_border)
    rb_index = msentence.tokenids.index(right_border)
    if rb_index < max(msentence.tokenids):
        #if this is not the last word of the sentence, include it in the clause
        rb_index += 1
    subjects_tokenid = None
    verbs_tokenid = None
    for tokenid in msentence.tokenids[lb_index:rb_index]:
        word = msentence.words[tokenid]
        if word.deprel in ('nsubj','предик','дат-субъект'):
            subjects_tokenid = tokenid
            #ALSO use the headtest:
            subjectshead = msentence.words[word.head]
            if subjectshead.tokenid < word.tokenid and subjectshead.pos == 'V' and 'INF' not in subjectshead.feat:
                return 1
            #-----------------------
        if word.IsThisFiniteVerb():
            verbs_tokenid = tokenid
    if subjects_tokenid and verbs_tokenid:
        if subjects_tokenid > verbs_tokenid:
            #if there is a subject and a finite verb and the verb precedes the subject, return 1
            return 1
    #Otherwise return 0
    return 0

def FirstWordOfClause(sentence, word):
    """Define, if this is potentially the first word of a clause"""
    if word.token in string.punctuation or word.pos in ('C') or word.token=='ettei':
        if word.lemma == 'ja' or word.lemma == 'и':
            #The conjunctions ja and i are problematic since they don't always begin a new clause
            if IsThisAClause(sentence,word):
                #if a potential clause beginning with 'ja' or 'i' has a verb, think of it as a clause
                return True
            #In addition, the borders of a relative clause might be problematic
        else:
            return True
    return False

def IsThisAClause(sentence, conjunction):
    """The conjunctions ja and i are problematic since they don't always begin a new clause. this
    is a method to try to define, whether something beginning with ja or i is actually  a clause.
    This method defines a potential clause not a clause if *no verb is found* (finite or infinite)
    """
    #Loop over the rest of the tokens in the sentence
    for tokenid in sentence.tokenids[sentence.tokenids.index(conjunction.tokenid) + 1:]:
        word = sentence.words[tokenid]
        if word.pos == 'V':
            #If a verb is found -> a clause
            try:
                headword = sentence.words[word.head]
                if headword.pos == 'N' and ('INF' in word.feat or 'PCP_' in word.feat or 'Vmps' in word.feat or 'Vmpp' in word.feat):
                    #... unless the verb is governed by a noun and the verb is an infinite form
                    pass
                else:
                    return True
            except KeyError:
                pass
        if word.token in string.punctuation or word.pos in ('C'):
            #if the border of the next clause was reached and no Verb found -> not counted as a clause
            return False
    #If the end of the sentence was reached -> not counted as a clause
    return False

def FirstLemmaOfCurrentClause(sentence, currentword):
    """Return the word object of the first lexical word object of the clause"""
    first_tokenid = sentence.FirstWordOfCurrentClause(currentword)
    firstword = sentence.words[first_tokenid]
    while firstword.token in string.punctuation:
        first_tokenid += 1
        firstword = sentence.words[first_tokenid]
    return firstword

def FirstLemmaOfNextClause(sentence, currentword):
    """Return the word object of the first lexical word object of the clause"""
    last_tokenid = sentence.LastWordOfCurrentClause(currentword)
    try:
        lastword = sentence.words[last_tokenid + 1]
        while lastword.token in string.punctuation:
            last_tokenid += 1
            lastword = sentence.words[last_tokenid]
    except KeyError:
        return None
    return lastword

def DefinePosChange(slpos,tlpos):
    """GIve a numeric representation to changes in tme position"""
    if slpos == tlpos:
        return 0
    elif slpos == 'clause-initial' and tlpos == 'middle':
        return 1
    elif slpos == 'clause-initial' and tlpos == 'clause-final':
        return 2
    elif slpos == 'clause-final' and tlpos == 'middle':
        return -1
    elif slpos == 'clause-final' and tlpos == 'clause-initial':
        return -2
    else:
        return 9

def SetUncertainAttribute(nullvalue, thisobject, attribute1, attribute2=''):
    """asdd"""
    if attribute2:
        try:
            obj = getattr(thisobject,attribute1)
            return  getattr(obj, attribute2)
        except AttributeError:
            return nullvalue
    else:
        try:
            return  getattr(thisobject, attribute1)
        except AttributeError:
            return nullvalue

def GetMetadata(text_id, metadata):
    """Get metadata for insertion to the results db"""
    for mdrow in metadata:
        if text_id == mdrow['id']:
            return mdrow
    return None

def ItemInString(stringlist,string):
    """Return true if one of the items in a list is in the string"""
    for item in stringlist:
        if item in string:
            return True
    return False

def DefineCase(word, lang):
    """Catch the case from the lemmatizers' output"""

    if word.pos in ('N','A'):
        if lang=='fi':
            try:
                p = re.compile('CASE_([a-z]+)',re.IGNORECASE)
                m = p.search(word.feat)
                return m.group(1)
            except AttributeError:
                return None
        if lang=='ru':
            return word.feat[4:5]
    else:
        return None

def DefineMorphology(word, lang):
    """Catch the case from the lemmatizers' output"""

    if word.pos in ('N','A'):
        if lang=='fi':
            return DefineCase(word,lang)
        if lang=='ru':
            #import ipdb; ipdb.set_trace()
            try:
                if word.headword.pos == 'S':
                    #if preposition as head
                    return '{}_{}'.format(word.headword.lemma,word.feat[4:5])
            except:
                pass
            #if no preposition as head:
            return word.feat[4:5]

    else:
        return None

def AssignDoubleLanguageValue(row,key,languagevalues):
    row['sl_' + key] = None
    row['tl_' + key] = None
    for langstatus, value in languagevalues.items():
        row[langstatus + '_' + key] = value
    return row

