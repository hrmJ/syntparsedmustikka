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

class MainMenu:
    """This class include all
    the comand line menu options and actions"""
    mainanswers =  {'q':'quit','l':'select language', 'm':'Monoconcordance'}

    def __init__(self):
        self.menu = multimenu(MainMenu.mainanswers)
        # Selectable options:
        self.selectedlang = 'none'
        #Control the program flow
        self.run = True

    def runmenu(self):
        'Run the main menu'
        #Clear the terminal:
        os.system('cls' if os.name == 'nt' else 'clear')
        #Build the selected options
        self.menu.question = 'Welcome\n\n' + '-'*20 + \
                          '''\n\nSelected options: 
                             \n\nLanguage:{} {}'''.format(self.selectedlang,'\n'*2 + '-'*20 + '\n'*2)
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
            Db.searched_table = 'ru_conll'
            self.selectedlang = 'fi'
        elif self.menu.answer == 'r':
            Db.searched_table = 'fi_conll'
            self.selectedlang = 'ru'

    def monoconc(self):
        #Initialize the search object
        thisSearch = Search()
        self.menu.question = 'Search type:'
        self.menu.validanswers = {'l':'lemmas','t':'tokens'}
        self.menu.prompt_valid()
        #Set the switch on if lemmatized chosen:
        self.menu.searchlemmas = self.menu.answer
        thisSearch.searchstring=input('\n\nGive a string to search:\n\n>')


    def MenuChooser(self,answer):
        if answer == 'q':
            self.run = False
            pass
        elif answer == 'l':
            self.chooselang()
        elif answer == 'm':
            self.monoconc()

#Start the menu

searchmenu = MainMenu()
while searchmenu.run == True:
    searchmenu.runmenu()
    pass
