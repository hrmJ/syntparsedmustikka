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
import os.path
#local modules
from dbmodule import mydatabase
from menus import Menu, multimenu, yesnomenu 
from search import Search, Match, Sentence, Word, ConstQuery, Db 
from phdqueries import FinnishTime, tmevalues
from filtermatches import FilterDuplicates1
import pickle
import datetime
import glob

class MainMenu:
    """This class include all
    the comand line menu options and actions"""
    mainanswers =  {'q':'quit','l':'select language', 'm':'Monoconcordance', 'd':'select database','p':'phdquery','s':'View searches','o':'View saved searches','n':'Нужно-search',
            'a':'advanced search','tme':'TME search'}

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


    def monoconc(self, advanced=False,tme=False):
        #Initialize the search object
        if not Db.searched_table :
            input('Please specify language first')
            return False
        thisSearch = Search(self.selecteddb)
        if advanced:
            cond = input('Give the category to be matched:')
            valuetuple = (input('\n\nGive a string to search:\n\n>'),)
            thisSearch.ConditionColumns.append({cond: valuetuple})
        elif tme:
            #Time measuring expressions
            thisSearch.ConditionColumns = tmevalues(self.selectedlang)
            if self.selectedlang == 'fi':
                thisSearch.headcond = {'column':'pos','values':('V',)}
                thisSearch.depcond = {'column':'!deprel','values':('cop',)}
            elif self.selectedlang == 'ru':
                # Accept cases where the head's pos is either V or S (prepositions)
                thisSearch.headcond = {'column':'pos','values':('V','S')}
        else:
            self.menu.question = 'Search type:'
            self.menu.validanswers = {'l':'lemmas','t':'tokens'}
            self.menu.prompt_valid()
            valuetuple = (input('\n\nGive a string to search:\n\n>'),)
            #Set the switch on if lemmatized chosen:
            if self.menu.answer == 'l':
                thisSearch.ConditionColumns.append({'lemma': valuetuple})
            elif self.menu.answer == 't':
                thisSearch.ConditionColumns.append({'token': valuetuple})
        #Build the query:
        thisSearch.BuildSubQuery()
        thisSearch.find()
        #Print the results:
        printResults(thisSearch)
        input('Press enter to continue.')

    def tmesearch(self):
        #Initialize the search object
        lang = input('Which language?')
        thisSearch =  TME(lang)
        #Build the query:
        thisSearch.BuildSubQuery()
        thisSearch.find()
        #Print the results:
        printResults(thisSearch)

    def phd(self):
        #Initialize the search object
        thisSearch = Search(self.selecteddb)
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

    def nuzhnosearch(self):
        #Initialize the search object
        thisSearch = Search(self.selecteddb)
        thisSearch.subquery = """
        SELECT align_id FROM {}
        WHERE lemma = %s
        """.format(Db.searched_table)
        thisSearch.searchtype= "nuzhno"
        thisSearch.searchstring = 'нужно'
        thisSearch.subqueryvalues=(thisSearch.searchstring,)
        thisSearch.find()
        #Print the results:
        printResults(thisSearch)
        input('Press enter to continue.')

    def viewsearches(self):
        """Take a look at the conducted searches and repeat / save them"""
        #collect the answers in a dict
        answlist = dict()
        for idx, searchobject in enumerate(Search.all_searches):
            answlist[str(idx)] = searchobject.name
        answlist['c'] = "Cancel"
        try:
            pickedsearch = Search.all_searches[int(self.menu.redifine_and_prompt('Select a search',answlist))]
            self.menu.redifine_and_prompt('What do you want to do with this search?',{'s':'save','r':'re-show the results'})
            if self.menu.answer == 's':
                filename = "savedsearches/{}_{}.p".format(pickedsearch.name,datetime.date.today())
                pickedsearch.filename = filename
                filenumber = 2
                while os.path.exists(filename):
                    filename = "savedsearches/{}_{}{}.p".format(pickedsearch.name,datetime.date.today(),filenumber)
                    pickedsearch.filename = filename
                    filenumber += 1
                pickle.dump(pickedsearch, open(filename, "wb"))
            elif self.menu.answer == 'r':
                printResults(pickedsearch)
            input('Press enter to continue')
        except:
            pass

    def viewsavedsearches(self):
        """Take a look at the saved searches and append them to the lsit of searches"""
        #collect the answers in a dict
        answlist = dict()
        if glob.glob('savedsearches/*.p'):
            for idx, savedsearch in enumerate(glob.glob('savedsearches/*.p')):
                answlist[str(idx)] = savedsearch
            answlist['c'] = "Cancel"
            pickedsearch = answlist[self.menu.redifine_and_prompt('Load a saved search:',answlist)]
            try:
                Search.all_searches.append(pickle.load( open(pickedsearch, "rb") ))
                print('Search {} loaded succesfully. Press "View searches" in the main menu to view it'.format(pickedsearch))
            except:
                print('No search loaded')
        else:
            print('No saved searches found.')
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
        elif answer == 'o':
            self.viewsavedsearches()
        elif answer == 'n':
            self.nuzhnosearch()
        elif answer == 'a':
            self.monoconc(True)
        elif answer == 'tme':
            self.monoconc(tme=True)

def printResults(thisSearch):
        if len(thisSearch.matches) >0:
            printmenu = multimenu({'a':'Print all','r':'Print max. 5 random','s':'Specify how many to print'})
            printmenu.question = 'Found {} occurences. What should I do?'.format(len(thisSearch.matches))
            printmenu.prompt_valid()
            if printmenu.answer == 's':
                #sort the dict to make sure its order stays the same
                matchitems = sorted(thisSearch.matches.items())
                printedsentences = resultprinter(matchitems, input('How many of the {} occurences should I print?'.format(len(thisSearch.matches))))
                pickedmatch = input('Select a sentence number to be visualized (empty cancels)')
                if pickedmatch in printedsentences:
                    printedsentences[pickedmatch].buildStringToVisualize()
                    printedsentences[pickedmatch].visualize()
                print('Sentence no {} visualized.'.format(pickedmatch))
        else:
            print('Sorry, nothing found.')
            print(thisSearch.subquery)
            print(thisSearch.subqueryvalues)


def resultprinter(matchitems,limit=1):
    """Print to screen the specified number of elements from search object"""
    printed = 0
    sentences = dict()
    for key, matches in matchitems:
        for match in matches:
            if printed == int(limit):
                break
            #match.monoConcordance()
            #match.matchedsentence.buildPrintString()
            match.BuildSentencePrintString()
            printed += 1
            print('{}:\t{}\nSentence id: {}, align id: {}\n'.format(printed,match.matchedsentence.printstring, match.matchedsentence.sentence_id, key))
            #Save the sentence so it can be referenced easily
            sentences[str(printed)] = match.matchedsentence
    return sentences


#Start the menu

if __name__ == "__main__":
    searchmenu = MainMenu()
    while searchmenu.run == True:
        searchmenu.runmenu()
        pass
