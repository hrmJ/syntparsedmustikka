#! /usr/bin/env python
import codecs
import csv
import sys
from collections import defaultdict
from lxml import etree
import string
import re
# For flushing the screen os-dependently
import os
#local modules
from dbmodule import mydatabase
from menus import Menu, multimenu, yesnomenu 
from search import Search, Match, Sentence, Word, ConstQuery, Db 
from phdqueries import FinnishTime
import pickle

class MainMenu:
    """This class include all
    the comand line menu options and actions"""
    mainanswers =  {'q':'quit','l':'select language', 'm':'Monoconcordance', 'd':'select database','p':'phdquery','s':'View searches'}

    def __init__(self):
        self.menu = multimenu(MainMenu.mainanswers)
        # Selectable options:
        self.selectedlang = 'none'
        self.selecteddb = 'none'
        #Control the program flow
        self.run = True

    def runmenu(self):
        'Run the main menu'
        #Clear the terminal:
        os.system('cls' if os.name == 'nt' else 'clear')
        #Build the selected options
        self.menu.question = 'Welcome\n\n' + '-'*20 + \
                          '''\n\nSelected options: 
                             \n\nDatabase: {}\nLanguage:{} {}
                             '''.format(self.selecteddb,self.selectedlang,'\n'*2 + '-'*20 + '\n'*2)
        self.menu.validanswers = MainMenu.mainanswers
        self.menu.prompt_valid()
        self.MenuChooser(self.menu.answer)
        #Show language if selected:

    def chooselang(self):
        self.menu.question = 'Select language: '
        self.menu.validanswers = {'f':'finnish','r':'russian'}
        self.menu.prompt_valid()
        #Evaluate:
        if self.menu.answer == 'f':
            Db.searched_table = 'fi_conll'
            self.selectedlang = 'fi'
        elif self.menu.answer == 'r':
            Db.searched_table = 'ru_conll'
            self.selectedlang = 'ru'


    def choosedb(self):
        self.menu.question = 'Select database: '
        self.menu.validanswers = {'1':'syntparfin','2':'syntparrus','3':'tbcorpfi','4':'tbcorpru'}
        self.menu.prompt_valid()
        Db.con = mydatabase(self.menu.validanswers[self.menu.answer],'juho')
        self.selecteddb = self.menu.validanswers[self.menu.answer]


    def monoconc(self):
        #Initialize the search object
        if not Db.searched_table :
            input('Please specify language first')
            return False
        thisSearch = Search()
        self.menu.question = 'Search type:'
        self.menu.validanswers = {'l':'lemmas','t':'tokens'}
        self.menu.prompt_valid()
        #Set the switch on if lemmatized chosen:
        if self.menu.answer == 'l':
            thisSearch.lemmas_or_tokens = 'lemma'
        elif self.menu.answer == 't':
            thisSearch.lemmas_or_tokens = 'token'
        thisSearch.searchstring = input('\n\nGive a string to search:\n\n>')
        #Build the query:
        thisSearch.subquery = """
        SELECT align_id FROM {}
        WHERE {} = %s
        """.format(Db.searched_table,thisSearch.lemmas_or_tokens)
        #The query values must be a tuple
        thisSearch.subqueryvalues=(thisSearch.searchstring,)
        thisSearch.find()
        #Print the results:
        printResults(thisSearch)
        input('Press enter to continue.')

    def phd(self):
        #Initialize the search object
        thisSearch = Search()
        print('Please wait, building the subquery.')
        FinnishTimeQuery = FinnishTime()
        thisSearch.subquery = FinnishTimeQuery.subq
        thisSearch.searchtype = 'phd'
        thisSearch.posvalues = FinnishTimeQuery.qwords
        #The query values must be a tuple
        thisSearch.subqueryvalues=()
        print('Starting the actual query.')
        thisSearch.find()
        printResults(thisSearch)
        input('Press enter to continue.')

    def viewsearches(self):
        """Take a look at the conducted searches and repeat / save them"""
        #collect the answers in a dict
        answlist = dict()
        for idx, searchobject in enumerate(Search.all_searches):
            answlist[str(idx)] = searchobject.name
        pickedsearch = self.menu.redifine_and_prompt('Select a search',answlist)
        self.menu.redifine_and_prompt('What do you want to do with this search?',{'s':'save','r':'re-show the results'})
        if self.menu.answer == 's':
            pass
        elif self.menu.answer == 'r':
            printResults(Search.all_searches[int(pickedsearch)])
        input('Press enter to continue')



    def MenuChooser(self,answer):
        if answer == 'q':
            self.run = False
        elif answer == 'l':
            self.chooselang()
        elif answer == 'm':
            self.monoconc()
        elif answer == 'd':
            self.choosedb()
        elif answer == 'p':
            self.phd()
        elif answer == 's':
            self.viewsearches()

def printResults(thisSearch):
        if len(thisSearch.matches) >0:
            limit = input('Found {} occurences, how many should I print?'.format(len(thisSearch.matches)))
            printed = 0
            for key, matches in thisSearch.matches.items():
                for match in matches:
                    if printed == int(limit):
                        break
                    #match.monoConcordance()
                    match.matchedsentence.buildPrintString()
                    printed += 1
                    print('{}:\n\n{}\n\n'.format(printed,match.matchedsentence.printstring))
        else:
            print('Sorry, nothing found.')
            print(thisSearch.subquery)
            print(thisSearch.subqueryvalues)

#Start the menu

searchmenu = MainMenu()
while searchmenu.run == True:
    searchmenu.runmenu()
    pass
