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
from termcolor import colored
import pickle
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
        """ HConstructs the actual condition. Values must be TUPLES."""
        condition = ''
        #This is to make sure psycopg2 uses the correct %s values
        sqlidx=0
        for column, value in ivaluedict.items():
            if condition:
                condition += " AND "
            #This is to make sure psycopg2 uses the correct %s values
            sqlRef = '{}cond{}'.format(parentidx,sqlidx)
            #If this is a neagtive condition
            if column[0] == '!':
                condition += "{} not in %({})s".format(column[1:],sqlRef)
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
            elif word.tokenid == self.matchedword.head:
                self.matchedsentence.Headhlprintstring += spacechar + '<' + word.token  + '>X'
                self.matchedsentence.printstring += spacechar + word.token
            else:
                self.matchedsentence.printstring += spacechar + word.token
                self.matchedsentence.Headhlprintstring += spacechar + word.token
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
