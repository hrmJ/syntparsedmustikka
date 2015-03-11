#! /usr/bin/env python
#Import modules
#Import modules{{{1
#For unicode support:
import codecs
#other
import csv
import sys
#xml parsing
from lxml import etree
#string operations
import string
import re
#local modules
from dbmodule import mydatabase
#1}}}
#classes
#classes{{{1
class Db:
#db{{{2
    """ A class to include some shared properties for the search and
    the match classes"""
    # What is the language table used in the queries
    searched_table = ''
    #a connection to db
    con = mydatabase('syntparfin','juho')
#2}}}

class Search:
#Search {{{2
    """This is the very
    basic class that is used to retrieve data from the corpus"""
    all_searches = []
    def __init__(self):
        self.matches = []
        #Save the search object to a list of all conducted searches during the session
        all_searches.append(self)

    def FindByToken(self, searchedvalue):
#FindByToken {{{3
        """ Locates the searched elements from the database  by the token of
        one word and collects the ids of the searched tokens"""
        #Collect ids from all the elements that match the search criterion 
        sql = "SELECT id, align_id, text_id, sentence_id FROM {} WHERE form = %s".format(Db.searched_table)
        rows = Db.con.dictquery(sql,(searchedvalue,))
        # Create match objects from the found tokens 
        for row in rows:
            self.matches.append(Match(row['id'],row['align_id'],row['text_id']))
#3}}}
#2}}}

class Match:
#Match {{{2
    # A list containing the ids of all the matches found
    def __init__(self,matched_id,align_id,text_id):
        #Build up the words, sentences and contexts {{{3
        self.align_id = align_id
        self.text_id = text_id
        sql_cols = "tokenid, form, lemma, pos, feat, head, deprel, align_id, id, sentence_id, text_id"
        sql = "SELECT {} FROM {} WHERE align_id = %s order by id".format(sql_cols, Db.searched_table)
        #fetch the whole context from the db
        wordrows = Db.con.dictquery(sql,(align_id,))
        #create a dict of sentence objects
        self.context = {}
        for wordrow in wordrows:
            if wordrow['sentence_id'] not in self.context:
                #If this sentence id not yet in the dict of sentences, add it
                self.context[wordrow['sentence_id']] = Sentence(wordrow['sentence_id'])
            #Add the current word to the list of words in the current sentence
            self.context[wordrow['sentence_id']].words.append(Word(wordrow,matched_id))
        #3}}}

    def monoConcordance(self):
        # COllect the context {{{3
        for sentence_id in sorted(self.context.keys()):
            self.context[sentence_id].buildPrintString()
            #Print out (just for testing)
            print("Sentence id {}:\n\t{}".format(sentence_id,self.context[sentence_id].printstring))

        #}}}3
#}}}2

class Sentence:
#Sentence{{{2
    """a sentence"""
    def __init__(self,sentence_id):
        self.sentence_id = sentence_id
        #initialize a list of words
        self.words = []

    def buildPrintString(self):
        #buildPrintString{{{3
        """Constructs a printable sentence"""
        self.printstring = ''
        for idx, word in enumerate(self.words):
            spacechar = ' '
            isqmark = False
            try:
                #if previous tag is a word:
                if self.words[idx-1].pos != 'Punct' and self.words[idx-1].token not in string.punctuation:
                    #...and this tag is a punctuation mark
                    if word.token in string.punctuation:
                        #..don't insert whitespace
                        spacechar = ''
                        #except if this is the first quotation mark
                        if word.token == '\"' and not isqmark:
                            isqmark = True
                            spacechar = ' '
                        elif word.token == '\"' and isqmark:
                            isqmark = False
                            spacechar = ''
            except:
                pass
            #if this is the first element in the context
            if idx == 0:
                spacechar = ''
            self.printstring += spacechar + word.token
        #}}}3
#}}}2

class Word:
#Word{{{2
    """A word object containing all the morhpological and syntactic information"""
    def __init__(self,row,matched_id):
        #Initialize all properties according to information from the database
        self.token = row["form"]
        self.lemma = row["lemma"]
        self.pos = row["pos"]
        self.feat = row["feat"]
        self.head = row["head"]
        self.deprel = row["deprel"] 
        self.tokenid = row["tokenid"] 
        #The general id in the db conll table
        self.dbid =  row["id"]
        if row["id"] ==  matched_id:
            self.ismatch = True
        else:

#}}}2
            
#1}}}

#Main module
#Main module{{{1
def main():
    #Set the language that is being searched
    Db.searched_table = 'fi_conll'
    newsearch = Search()
    newsearch.FindByToken('oli')
    newsearch.matches[1].monoConcordance()
    #for s_id, sentence in newsearch.matches[1].context:
    #    print (sentence)
    #searchedelement.FetchParallelConcordance()
#1}}}
#Start the script
#Start the script{{{1
if __name__ == "__main__":
    main()
#1}}}
