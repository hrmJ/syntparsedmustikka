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
import pickle
#local modules
from dbmodule import mydatabase, psycopg
from menus import Menu, multimenu, yesnomenu 
from itertools import chain
from progress.bar import Bar
from texttable import Texttable, get_color_string, bcolors
import time
import datetime
from statistics import mean, median

class Db:
    """ A class to include some shared properties for the search and
    the match classes"""
    # What is the language table used in the queries
    searched_table = ''
    #a connection to db
    con = mydatabase('syntparfin','juho')

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

    def Save(self):
        """Save the search object as a pickle file"""
        pickle.dump(self, open(self.filename, "wb"))
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
        self.subquery = """SELECT align_id FROM {} WHERE {} """.format(Db.searched_table,MultipleValuePairs)

    def BuildSubqString(self, ivaluedict,parentidx):
        """ Constructs the actual condition. Values must be TUPLES."""
        condition = ''
        sqlidx=0
        for column, value in ivaluedict.items():
            #Make sure the user gives the values as tuples (excluding fuzzy matches)
            if column[0] != '?' and not isinstance(value,tuple):
                raise TypeError('The values in the ConditionColumn lists dict must be tuples, see {}:{}'.format(column,value))
            if condition:
                condition += " AND "
            #This is to make sure psycopg2 uses the correct %s values
            sqlRef = '{}cond{}'.format(parentidx,sqlidx)
            #If this is a neagtive condition
            if column[0] == '!':
                condition += "{} not in %({})s".format(column[1:],sqlRef)
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
        sql_cols = "tokenid, token, lemma, pos, feat, head, deprel, align_id, id, sentence_id, text_id, contr_deprel, contr_head"
        sqlq = "SELECT {0} FROM {1} WHERE align_id in ({2}) AND text_id = 5 order by align_id, id".format(sql_cols, Db.searched_table, self.subquery)
        wordrows = Db.con.dictquery(sqlq,self.subqueryvalues)
        print('Analyzing...')
        self.pickFromAlign_ids(wordrows)



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

    def processWordsOfSentence(self,alignkey,sentencekey):
        """ Process every word of a sentence and chek if a search condition is met.
        The purpose of this function is to simplify the pickFromAlign_ids function"""
        # The sentence is processed word by word
        for wkey, word in self.aligns[alignkey][sentencekey].words.items():
            if self.evaluateWordrow(word,self.aligns[alignkey][sentencekey]):  
                #if the evaluation function returns true
                self.aligns[alignkey][sentencekey].matchids.append(word.tokenid)

    def ProcessSentencesOfAlign(self, alignkey):
        """WARNING the keys should probably be converted to INTS
           Process all the sentences in the previous align unit and check for matches
           variables:
           alignkey = the key of the align segment to be processed
           """
        for sentence_id in sorted(self.aligns[alignkey].keys()):
            #Process all the matches in the sentence that contained one or more matches
            for matchid in self.aligns[alignkey][sentence_id].matchids:
                self.matches[alignkey].append(Match(self.aligns[alignkey],matchid,sentence_id))


    def evaluateWordrow(self, word,sentence):
        'Test a word (in a sentence) according to criteria'
        if self.searchtype == 'phd':
            #If this lemma is not listed in the list of search words
            if not self.posvalues[word.lemma]:
                return False
            #if this pos is not listed as a possible one for the lemma
            if word.pos not in self.posvalues[word.lemma]:
                return False
            #if this word's deprel not listed
            if word.deprel not in ('advmod','nommod','dobj','adpos'):
                return False
            #if the word's head's deprel not listed
            if sentence.words[word.head].deprel not in ('ROOT','advcl','cop','aux'):
                return False
        elif self.searchtype == 'nuzhno':
            nomatch = True
            for wkey in sorted(map(int,sentence.words)):
                wordinsent = sentence.words[wkey]
                if wordinsent.head == word.tokenid and wordinsent.feat[-2:] == 'dn' and wordinsent.deprel != '2-компл':
                    nomatch = False
                    break
            if nomatch:
                return False
            if word.lemma not in ('нужно','надо','должно'):
                return False
        elif self.searchtype == 'semsubj_gen':
            nomatch = False
            for wkey in sorted(map(int,sentence.words)):
                wordinsent = sentence.words[wkey]
                #If the examined word's head is 'kuluttua' don't accept
                if wordinsent.head == word.tokenid and (wordinsent.token == 'kuluttua' or (wordinsent.pos != 'V' and wordinsent.deprel != 'ROOT')):
                    nomatch = True
                    break
            if nomatch:
                return False
            #If this is not a subject in genetive, don't accept
            if word.deprel != 'nsubj' or 'CASE_Gen' not in word.feat:
                return False
        #-------------------------------------------------------------------------------------
        else:
            #If this is a standard search
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
            fulfills=True
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
        print('Assign the correct target segment for each match...')
        for align_id, matches in self.matches.items():
            for match in matches:
                match.parallelcontext = self.parallel_aligns[align_id]
        print('Done.')

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

class Match:
    """ 
    A match object contains ifromation about a concrete token that 
    is the reason for a specific match to be registered.
    """
    # A list containing the ids of all the matches found
    def __init__(self,alignsegment,matchid,sentence_id):
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

    def postprocess(self,rejectreason):
        """If the user wants to filter the matches and mark some of them manually as accepted and some rejected"""
        self.postprocessed = True
        self.rejectreason = rejectreason

    def BuildSentencePrintString(self):
        """Constructs a printable sentence and highliths the match
        """
        self.matchedsentence.printstring = ''
        #create an string also without the higlight
        self.matchedsentence.cleanprintstring = ''
        self.matchedsentence.colorprintstring = ''
        self.matchedsentence.Headhlprintstring = ''
        isqmark = False
        for idx in sorted(self.matchedsentence.words.keys()):
            spacechar = ' '
            word = self.matchedsentence.words[idx]
            try:
                previous_word = self.matchedsentence.words[idx-1]
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
            if word.tokenid == self.matchedword.tokenid:
                #Surround the match with <>
                self.matchedsentence.printstring += spacechar + '<' + word.token  + '>'
                self.matchedsentence.Headhlprintstring += spacechar + '<<' + word.token  + '>>Y'
                self.matchedsentence.colorprintstring += spacechar + bcolors.GREEN + word.token + bcolors.ENDC 
            elif word.tokenid == self.matchedword.head:
                self.matchedsentence.Headhlprintstring += spacechar + '<' + word.token  + '>X'
                self.matchedsentence.printstring += spacechar + word.token
                self.matchedsentence.colorprintstring += spacechar + word.token
            else:
                self.matchedsentence.printstring += spacechar + word.token
                self.matchedsentence.colorprintstring += spacechar + word.token
                self.matchedsentence.Headhlprintstring += spacechar + word.token
            self.matchedsentence.cleanprintstring += spacechar + word.token

    def CatchHead(self):
        """Store the matches head in a separate object,if possible. If not, return the sentence's id"""
        try:
            self.headword = self.matchedsentence.words[self.matchedword.head]
        except KeyError:
            return False
        if self.parallelword:
            #if there is a parallel context
            try:
                self.parallel_headword = self.parallelsentence.words[self.parallelword.head]
            except KeyError:
                pass
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
        parmenu = multimenu({'y':'yes','n':'no','s':'syntactically dissimilar'})
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
        #If nothing was accepted, return false
        return False

    def PickTargetSentence(self):
        """Prints out a menu of all the target sentences"""
        #if nothing was found or nothing was an actual match
        sentencemenu = multimenu({})
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
        for tokenid, word in self.parallelsentence.words.items():
            if word.token not in string.punctuation:
                wordmenu.validanswers[str(tokenid)] = word.token
        wordmenu.cancel = 'No single word can be specified'
        wordmenu.prompt_valid('Wich word is the closest match to {}?'.format(self.matchedword.token))
        if wordmenu.answer != 'n':
            #SET the parallel word:
            self.parallelword = self.parallelsentence.words[int(wordmenu.answer)]
            return True
            #######
        else:
            return False

    def DefinePositionMatch(self):
        """Define what part of the match is the direct  dependent of a verb etc"""
        self.positionmatchword = self.matchedword
        if self.parallelword:
            #If there is a comparable parallel context
            self.parallel_positionword = self.parallelword
        #Check the words head
        self.CatchHead()
        if self.headword.pos in ('S'):
            #if the match is actually a dependent of a pronoun
            # LIST all the other possible cases as well!
            self.positionmatchword = self.headword
            self.headword = self.matchedsentence.words[self.positionmatchword.head]
            if self.parallelword:
                #If there is a comparable parallel context
                self.parallel_positionword = self.parallel_headword
                self.parallel_headword = self.parallelsentence.words[self.parallel_positionword.head]

    def DefinePosition1(self):
        """Define, whether the match is located clause-initially, clause-finally or in the middle"""
        self.DefinePositionMatch()
        #For the source segment
        if IsThisClauseInitial(self.positionmatchword, self.matchedsentence):
            self.sourcepos1 = 'clause-initial'
        else:
            self.sourcepos1 = 'middle'
        #For the target segment
        if self.parallelword:
            if IsThisClauseInitial(self.parallel_positionword, self.parallelsentence):
                self.targetpos1 = 'clause-initial'
            else:
                self.targetpos1 = 'middle'


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
            if word.tokenid in self.matchids:
                self.printstring += spacechar + '*' + word.token  + '*'
            else:
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
        """Return the first word of the clause specified by a word"""
        self.tokenids = sorted(map(int,self.words))
        this_tokenid = currentword.tokenid
        while not FirstWordOfClause(self.words[this_tokenid]) and this_tokenid > min(self.tokenids):
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
        while not FirstWordOfClause(self.words[this_tokenid]) and this_tokenid < max(self.tokenids):
            this_tokenid += 1
            if this_tokenid == max(self.tokenids):
                # if this is the last word of the whole sentence
                return this_tokenid
        #If a marker for the next clause was met, assume that the previous word was the last of the current clause:
        return this_tokenid - 1

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
        self.contr_deprel =  row["contr_deprel"]

    def printAttributes(self):
        print('Attributes of the word:\n token = {} \n lemma = {} \n feat = {} \n  pos = {}'.format(self.token,self.lemma,self.feat,self.pos))


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
    this_tokenid = msentence.FirstWordOfCurrentClause(mword)
    #2. Find out what's between the punctuation mark / conjunction / sentence border and the match
    #First, assume this IS clause-initial
    clauseinitial = True
    if this_tokenid == min(msentence.tokenids):
        #If this is the first clause of the sentence
        clauseborder = 0
    else:
        clauseborder = msentence.tokenids.index(this_tokenid)+1
    matchindex = msentence.tokenids.index(mword.tokenid)
    tokenids_beforematch = msentence.tokenids[clauseborder:matchindex]
    #import ipdb; ipdb.set_trace()
    for tokenid in tokenids_beforematch:
        #if there is a word between the bmarker and the match, assume that the match is not clause-initial 
        clauseinitial = False
        word = msentence.words[tokenid]
        if word.head == mword.tokenid \
            or word.pos == 'C':
            #except if this is a depent of the match or a conjunction
            clauseinitial = True
        else:
            #If all the above tests fail, then assume that there is a word before the match in the clause
            break
    return clauseinitial

def IsThisClauseFinal(mword, msentence):
    """Define, whether the match is located clause-initially"""
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
        lastwordindex = msentence.tokenids.index(this_tokenid) + 1 
        tokenids_aftermatch = msentence.tokenids[matchindex:lastwordindex]

    #First, assume this IS clause-final
    clausefinal = True
    #import ipdb; ipdb.set_trace()
    for tokenid in tokenids_aftermatch:
        #if there is a word between the bmarker and the match, assume that the match is not clause-final 
        clausefinal = False
        word = msentence.words[tokenid]
        if word.head == mword.tokenid \
            or word.pos == 'C':
            #except if this is a depent of the match or a conjunction
            clausefinal = True
        else:
            #If all the above tests fail, then assume that there is a word before the match in the clause
            break
    return clausefinal

def FirstWordOfClause(word):
    """Define, if this is potentially the first word of a clause"""
    if word.token in string.punctuation or \
    word.pos in ('C'):
        return True
    return False
