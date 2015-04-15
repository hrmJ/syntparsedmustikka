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
    def __init__(self):
    # The matches will be saved as lists in a dict with align_ids as keys.
        self.matches = defaultdict(list)
        #Save the search object to a list of all conducted searches during the session
        Search.all_searches.append(self)
        # save an id for the search for this session
        self.searchid = id(self)
        #Ask a name for the search (make this optional?)
        self.name = input('Give a name for this search:\n\n>')

    def FindByToken(self, searchedvalue):
        """ Locates the searched elements from the database  by the token of
        one word and collects the ids of the searched tokens"""
        #Collect ids from all the elements that match the search criterion 
        sql = "SELECT id, align_id, text_id, sentence_id FROM {} WHERE token = %s".format(Db.searched_table)
        rows = Db.con.dictquery(sql,(searchedvalue,))
        # Create match objects from the found tokens 
        counter=0
        for row in rows:
            counter += 1
            #self.matches.append(Match(row['id'],row['align_id'],row['text_id']))
        print('Found {} occurences'.format(counter))

    def FindByQuery(self, sqlq, sqlvalue):
        """Locates elements using user-defined queries"""
        #Collect ids from all the elements that match the search criterion 
        rows = Db.con.dictquery(sqlq,(sqlvalue,))
        # Create match objects from the found tokens 
        counter=0
        for row in rows:
            counter += 1
            self.matches.append(Match(row['id'],row['align_id'],row['text_id']))
        print('Found {} occurences'.format(counter))

    def FindByQuery2(self, sqlq, sqlvalue):
        """Locates elements using user-defined queries"""
        sql_cols = "tokenid, token, lemma, pos, feat, head, deprel, align_id, id, sentence_id, text_id"
        #Fetch everything from the align units that  are retrieved by the user-defined query
        sqlq = "SELECT {0} FROM {1} WHERE align_id in ({2}) order by align_id, id".format(sql_cols, Db.searched_table, sqlq)
        # Notice that the %s matchin the sqlvalue here must be defined in the query!
        wordrows = Db.con.dictquery(sqlq,(sqlvalue,))
        #create a dict of sentence objects
        context = dict()
        #create a dict of align segments
        aligns = dict()
    #currentalign = {'sentences':list(),'id':0}
    #Todo: HOW ABOUT THE LAST ALIGNMENT UNIT!
        for wordrow in wordrows:
            if wordrow['align_id'] not in aligns:
                if aligns:
                    #If this is not the first word of the first sentence:
                    #..that means that there has already been at least one sentence
                    # .. and we'll first process that sentence
                    for whead, word in aligns[previous_align][previous_sentence].words.items():
                        #This is where the actual test is: >>>>>>>>>>>>>>>>
                        if  word.lemma == sqlvalue and (aligns[previous_align][previous_sentence].words[word.head].deprel == 'ROOT'):
                            #the word that is the actual word match is recorded as an attribute of the sentence object with a tokenid as its value
                            aligns[previous_align][previous_sentence].matchids.append(word.tokenid)
                    #now, let's process the whole previous align segment (with one or more sentences)
                    #WARNING the keys should probably be converted to INTS
                    for sentence_id in sorted(aligns[previous_align].keys()):
                        #for all the sentences in the previous align unit that included a match or matches
                        for matchid in aligns[previous_align][sentence_id].matchids:
                            self.matches[previous_align].append(Match(aligns[previous_align],matchid,sentence_id))
                aligns[wordrow['align_id']] = dict()
                previous_align = wordrow['align_id']
            if wordrow['sentence_id'] not in aligns[wordrow['align_id']]:
                #If this sentence id not yet in the dict of sentences, add it
                if aligns and aligns[previous_align]:
                    #If this is not the first word of the first sentence:
                    #how about if this is the last sentence? ORDER OF THIS WORD DICT!!
                    for whead, word in aligns[wordrow['align_id']][previous_sentence].words.items():
                        if  word.lemma == sqlvalue and (aligns[wordrow['align_id']][previous_sentence].words[word.head].deprel == 'ROOT'):
                            #the word that is the actual word match is recorded as an attribute of the sentence object with a tokenid as its value
                            aligns[wordrow['align_id']][previous_sentence].matchids.append(word.tokenid)
                            #self.matches[word.align_id].append(Match())
                            #if the word's lemma matches the searched one and the word's head is the ROOT or ..
                            # Add this sentence to this align unit
                aligns[wordrow['align_id']][wordrow['sentence_id']] = Sentence(wordrow['sentence_id'])
                previous_sentence = wordrow['sentence_id']
            # Add all the information about the current word as a Word object to the sentence
            aligns[wordrow['align_id']][wordrow['sentence_id']].words[wordrow['tokenid']] = Word(wordrow)


    def find(self):
        """Query the database according to instructions from the use
        The search.subquery attribute can be any query that selects a group of align_ids
        From the syntpar...databases
        """
        sql_cols = "tokenid, token, lemma, pos, feat, head, deprel, align_id, id, sentence_id, text_id"
        sqlq = "SELECT {0} FROM {1} WHERE align_id in ({2}) order by align_id, id".format(sql_cols, Db.searched_table, self.subquery)
        wordrows = Db.con.dictquery(sqlq,self.subqueryvalues)
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
        #Finally, process all the sentences in the last align unit that included a match or matches
        self.ProcessSentencesOfAlign(previous_align)

    def processWordsOfSentence(self,alignkey,sentencekey):
        """ Process every word of a sentence and chek if a search condition is met.
        The purpose of this function is to simplify the pickFromAlign_ids function"""
        # The sentence is processed word by word
        for wkey, word in self.aligns[alignkey][sentencekey].words.items():
            #This is where the actual test is:
            if self.evaluateWordrow(word):  
            #------------------------------------------------------------
                #if the evaluation function returns true
                self.aligns[alignkey][sentencekey].matchids.append(word.tokenid)

    def ProcessSentencesOfAlign(self, alignkey):
        """WARNING the keys should probably be converted to INTS
           Process all the sentences in the previous align unit and check for matches matches"""
        for sentence_id in sorted(self.aligns[alignkey].keys()):
            #Process all the matches in the sentence that contained one or more matches
            for matchid in self.aligns[alignkey][sentence_id].matchids:
                self.matches[alignkey].append(Match(self.aligns[alignkey],matchid,sentence_id))


    def evaluateWordrow(self, word):
        'Test a word (in a sentence) according to criteria'
        #if word.lemma == sqlvalue and (aligns[previous_align][previous_sentence].words[word.head].deprel == 'ROOT'):
        #if word.lemma == sqlvalue and (aligns[wordrow['align_id']][previous_sentence].words[word.head].deprel == 'ROOT'):
        #if word.lemma == sqlvalue and (aligns[previousalign][previous_sentence].words[word.head].deprel == 'ROOT'):
        #if word.lemma == sqlvalue and (aligns[thisalign    ][previous_sentence].words[word.head].deprel == 'ROOT'):
        if getattr(word, self.lemmas_or_tokens) != self.searchstring:
            #if the lemma or the token isn't what's being looked for, quit as a non-match
            return False
        #if all tests passed, return True
        return True

class Match:
    # A list containing the ids of all the matches found
    def __init__(self,alignsegment,matchid,sentence_id):
        #self.text_id = text_id
	#DEAL WITH MATCHID
        #Get the sentence where the match is
        self.context = alignsegment
        self.matchedsentence = alignsegment[sentence_id]

    def monoConcordance(self):
    #WARNING! the keys should probably be converted to ints
        for sentence_id in sorted(self.context.keys()):
            self.context[sentence_id].buildPrintString()
            #Print out (just for testing)
            print("Sentence id {}:\n\t{}".format(sentence_id,self.context[sentence_id].printstring))


class Sentence:
    """a sentence"""
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
            self.printstring += spacechar + word.token

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
        #The general id in the db conll table
        self.dbid =  row["id"]


#Main module

def main():
    #Set the language that is being searched
    #Db.searched_table = 'fi_conll'
    Db.searched_table = 'ru_conll'
    newsearch = Search()
    newsearch.FindByQuery2(ConstQuery.independentByLemma2,'уже')
    for key, matches in newsearch.matches.items():
        for match in matches:
            #match.monoConcordance()
            match.matchedsentence.buildPrintString()
            print(match.matchedsentence.printstring)
            sys.exit(0)
#Start the script
if __name__ == "__main__":
    main()
