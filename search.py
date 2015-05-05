#! /usr/bin/env python
#Import modules
import codecs
import csv
import sys
import os
from collections import defaultdict
from lxml import etree
import string
import re
#local modules
from dbmodule import mydatabase
from menus import Menu, multimenu, yesnomenu 
#classes
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
    def __init__(self,queried_db=''):
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
        self.name = input('Give a name for this search:\n\n>')
        if not self.name:
            self.name = 'unnamed_{}'.format(len(Search.all_searches))
        self.searchtype = 'none'
        #Record information about db
        self.queried_db = queried_db
        self.queried_table = Db.searched_table

    def find(self):
        """Query the database according to instructions from the user
        The search.subquery attribute can be any query that selects a group of align_ids
        From the syntpar...databases
        """
        sql_cols = "tokenid, token, lemma, pos, feat, head, deprel, align_id, id, sentence_id, text_id"
        sqlq = "SELECT {0} FROM {1} WHERE align_id in ({2}) order by align_id, id".format(sql_cols, Db.searched_table, self.subquery)
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
        else:
            if getattr(word, self.lemmas_or_tokens) != self.searchstring:
                #if the lemma or the token isn't what's being looked for, quit as a non-match
                return False
            #if all tests passed, return True
        return True

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
        #self.text_id = text_id
        self.context = alignsegment
        self.matchedsentence = alignsegment[sentence_id]
        self.matchedword = alignsegment[sentence_id].words[matchid]
        self.sourcetextid = self.matchedword.sourcetextid

    def BuildSentencePrintString(self):
        """Constructs a printable sentence and highliths the match
        """
        self.matchedsentence.printstring = ''
        #create an string also without the higlight
        self.matchedsentence.cleanprintstring = ''
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
            else:
                self.matchedsentence.printstring += spacechar + word.token
            self.matchedsentence.cleanprintstring += spacechar + word.token


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
