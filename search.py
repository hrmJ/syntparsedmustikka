#! /usr/bin/env python
#Import modules
#Import modules{{{1
#For unicode support:
import codecs
#other
import csv
import sys
from collections import defaultdict
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

class ConstQuery:
#ConstQuery{{{2
    """Some often used queries can be saved as instances of this class"""
    # What is the language table used in the queries
    independentByLemma2 ="""SELECT lemmaQ.align_id FROM 
                            (SELECT * FROM {0} WHERE lemma = %s) as lemmaQ, {0}
                                WHERE {0}.tokenid = lemmaQ.head AND 
                                {0}.sentence_id = lemmaQ.sentence_id AND
                                {0}.deprel='ROOT'""".format('fi_conll')
    independentByLemma ="""SELECT lemmaQ.id, lemmaQ.align_id, lemmaQ.text_id, lemmaQ.sentence_id FROM 
                            (SELECT * FROM {0} WHERE lemma = %s) as lemmaQ, {0}
                                WHERE {0}.tokenid = lemmaQ.head AND 
                                {0}.sentence_id = lemmaQ.sentence_id AND
                                {0}.deprel='ROOT'""".format('fi_conll')
#2}}}

class Search:
    #Search {{{2
    """This is the very
    basic class that is used to retrieve data from the corpus"""
    all_searches = []
    def __init__(self):
    # The matches will be saved as lists in a dict with align_ids as keys.
        self.matches = defaultdict(list)
        #Save the search object to a list of all conducted searches during the session
        Search.all_searches.append(self)

    def FindByToken(self, searchedvalue):
    #FindByToken {{{3
        """ Locates the searched elements from the database  by the token of
        one word and collects the ids of the searched tokens"""
        #Collect ids from all the elements that match the search criterion 
        sql = "SELECT id, align_id, text_id, sentence_id FROM {} WHERE form = %s".format(Db.searched_table)
        rows = Db.con.dictquery(sql,(searchedvalue,))
        # Create match objects from the found tokens 
        counter=0
        for row in rows:
            counter += 1
            #self.matches.append(Match(row['id'],row['align_id'],row['text_id']))
        print('Found {} occurences'.format(counter))
    #3}}}
    def FindByQuery(self, sqlq, sqlvalue):
    #FindByToken {{{3
        """Locates elements using user-defined queries"""
        #Collect ids from all the elements that match the search criterion 
        rows = Db.con.dictquery(sqlq,(sqlvalue,))
        # Create match objects from the found tokens 
        counter=0
        for row in rows:
            counter += 1
            self.matches.append(Match(row['id'],row['align_id'],row['text_id']))
        print('Found {} occurences'.format(counter))
    #3}}}
    def FindByQuery2(self, sqlq, sqlvalue):
    #FindByQuery2 {{{3
        """Locates elements using user-defined queries"""
        sql_cols = "tokenid, form, lemma, pos, feat, head, deprel, align_id, id, sentence_id, text_id"
        #Fetch everything from the align units that  are retrieved by the user-defined query
        sqlq = "SELECT {0} FROM {1} WHERE align_id in ({2}) order by align_id, id".format(sql_cols, Db.searched_table, sqlq)
        # Notice that the %s matchin the sqlvalue here must be defined in the query!
        wordrows = Db.con.dictquery(sqlq,(sqlvalue,))
        #create a dict of sentence objects
        context = dict()
        #create a dict of align segments
        aligns = dict()
    #currentalign = {'sentences':list(),'id':0}
    #HOW ABOUT H*THE LAST ALIGNMENT UNIT!
        for wordrow in wordrows:
            if wordrow['align_id'] not in aligns:
                if aligns:
                    #If this is not the first word of the first sentence:
                    #..that means that there has already been at least one sentence
                    # .. and we'll first process that sentence
                    for whead, word in aligns[previous_align][previous_sentence].words.items():
                        if  word.lemma == sqlvalue and (aligns[previous_align][previous_sentence].words[word.head].deprel == 'ROOT'):
                            #the word that is the actual word match is recorded as an attribute of the sentence object with a tokenid as its value
                            aligns[previous_align][previous_sentence].matchids.append(word.tokenid)
                    #now, let's process the whole previous align segment (with one or more sentences)
                    #WARNING the keys should probably be converted to INTS
                    for sentence_id in sorted(aligns[previous_align].keys()):
                        #for all the sentences in the previous align unit that included a match or matches
                        for matchid in aligns[previous_align][sentence_id].matchids:
                            self.matches[previous_align].append(Match(aligns[previous_align],matchid))
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
    #3}}}
    #2}}}

class Match:
#Match {{{2
    # A list containing the ids of all the matches found
    def __init__(self,alignsegment,matchid):
        #Build up the words, sentences and contexts {{{3
        #self.text_id = text_id
	#DEAL WITH MATCHID
        self.context = alignsegment
        #3}}}

    def monoConcordance(self):
        # COllect the context {{{3
    #WARNING! the keys should probably be converted to ints
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
        #initialize a dict of words. The word's ids in the sentence will be used as keys
        self.words = dict()
        #By default, the sentence's matchids attribute is an empty list = no matches in this sentence
        self.matchids = list()

    def buildPrintString(self):
        #buildPrintString{{{3
        """Constructs a printable sentence"""
        self.printstring = ''
        isqmark = False
        for idx in sorted(self.words.keys()):
            spacechar = ' '
            word = self.words[idx]
            idx = int(idx)
            try:
                #if previous tag is a word:
                if self.words[str(idx-1)].pos != 'Punct' and self.words[str(idx-1)].token not in string.punctuation:
                    #...and this tag is a punctuation mark. Notice that exception is made for hyphens, since in mustikka they are often used as dashes
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
                elif self.words[str(idx-1)].form in string.punctuation:
                    #...and this tag is a punctuation mark
                    if (self.word.token in string.punctuation and self.word.token != '-' and self.word.token != '\"') or isqmark:
                        #..don't insert whitespace
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
    def __init__(self,row):
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

#}}}2
            
#1}}}

#Main module
#Main module{{{1
def main():
    #Set the language that is being searched
    Db.searched_table = 'fi_conll'
    newsearch = Search()
    ConstQuery.independentByLemma += 'LIMIT 10'
    #newsearch.FindByQuery(ConstQuery.independentByLemma,'jo')
    newsearch.FindByQuery2(ConstQuery.independentByLemma2,'jo')
    for key, matches in newsearch.matches.items():
        for match in matches:
            match.monoConcordance()
            sys.exit(0)
      #  for thismatch in match:
      #      thismatch.monoConcordance()
      #      sys.exit(0)
    #print(newsearch.matches[1])
    #newsearch.matches[1].monoConcordance()
    ##for s_id, sentence in newsearch.matches[1].context:
    #    print (sentence)
    #searchedelement.FetchParallelConcordance()
#1}}}
#Start the script
#Start the script{{{1
if __name__ == "__main__":
    main()
#1}}}
