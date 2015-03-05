#! /usr/bin/env python
#Import modules{{{1
#For unicode support:
import codecs
#other
import csv
import sys
#xml parsing
from lxml import etree
#local modules
from dbmodule import mydatabase
#classes {{{1
class Search:
    """This is the very
    basic class that is used to retrieve data from the corpus"""
# What is the language table used in the queries
    searched_table = ''
#a connection to db
    con = mydatabase('syntparfin','juho')
    def __init__(self,searched_table):
        """ Initialize a new search object. Set the table value to the language
        chosen"""
        Search.searched_table = searched_table;
    def FindSingleToken(self, searchedvalue):
        """ Locates the searched elements from the database  by the token of
        one word and collects the ids of the searched tokens"""
#Collect ids from all the elements that match the search criterion
        sql = "SELECT id, align_id, text_id, sentence_id FROM {} WHERE form = %s".format(Search.searched_table)
        rows = self.con.dictquery(sql,(searchedvalue,))
# Create match objects from the found tokens
        for row in rows:
            thismatch =  Match(Search.searched_table)
            thismatch.token_id = row['id']
            thismatch.sentence_id = row['sentence_id']
            thismatch.align_id = row['align_id']
            thismatch.text_id = row['text_id']
class Match:
# A list containing the ids of all the matches found
    searched_table = ''
    all_matches = []
    con = mydatabase('syntparfin','juho')
    def __init__(self, searched_table):
#Initialize: add this match to the list of all matches
        Match.all_matches.append(self)
        Match.searched_table = searched_table
    def FetchParallelConcordance(self):
# COllect the context
        sql = "SELECT form FROM {} WHERE align_id = %s order by id".format(Match.searched_table)
        words = self.con.dictquery(sql,(self.align_id,))
        self.context = ""
        for word in words:
            self.context += word[0] + " "
            
#1}}}
#Main module{{{1
def main():
    mysearch = Search('fi_conll')
    mysearch.FindSingleToken('oli')
    Match.all_matches[0].FetchParallelConcordance()
    print(Match.all_matches[0].context)
    #searchedelement.FetchParallelConcordance()
#Start the script{{{1
if __name__ == "__main__":
    main()
#1}}}
