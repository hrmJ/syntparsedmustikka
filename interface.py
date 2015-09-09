#! /usr/bin/env python
import codecs
import random
import csv
from deptypetools import makeSearch
import sys
from collections import defaultdict
from lxml import etree
import string
import re
# For flushing the screen os-dependently
import os
import os.path
#local modules
from dbmodule import mydatabase, psycopg
from menus import Menu, multimenu, yesnomenu 
from search import Search, Match, Sentence, Word, ConstQuery, Db 
from phdqueries import FinnishTime, tmevalues
from filtermatches import FilterDuplicates1
import pickle
import datetime
import glob
from texttable import Texttable, get_color_string, bcolors

class MainMenu:
    """This class include all
    the comand line menu options and actions"""
    mainanswers =  {'q':'quit','l':'select language', 'm':'Monoconcordance', 
            'd':'select database','p':'phdquery','s':'View searches','o':'View saved searches','n':'Нужно-search',
            'a':'advanced search','tme':'TME search','cs':'Corpus stats','pc':'parallel concordance'}

    def __init__(self):
        self.menu = multimenu(MainMenu.mainanswers)
        # Selectable options:
        self.selectedlang = 'none'
        self.selecteddb = 'none'
        self.columns = dict()
        #Control the program flow
        self.run = True
        self.pause = False

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
        self.menu.validanswers = {'1':'syntparfin','2':'syntparrus','3':'tbcorpfi','4':'tbcorpru','5':'syntparrus2','6':'syntparfin2'}
        self.menu.prompt_valid()
        Db.con = mydatabase(self.menu.validanswers[self.menu.answer],'juho')
        self.selecteddb = self.menu.validanswers[self.menu.answer]

    def Parconc(self):
        self.AddConditions()
        self.search = makeSearch(database=Db.con.dbname, dbtable=Db.searched_table, ConditionColumns=self.condcols,isparallel=True)
        printResults(self.search)

    
    def AddConditions(self):
        """Parallel concordance search"""
        self.ListColumns()
        columns = multimenu(self.columns)
        self.condcols = dict()
        addmore = multimenu({'y':'add more','q':'stop adding conditions'})
        newvals = multimenu({'q':'stop adding values','y':'insert next possible value'})
        newvals.answer = 'y'
        addmore.answer = 'y'
        while addmore.answer == 'y':
            vals = list()
            columns.prompt_valid('What column should the condition be based on?')
            newvals.answer = 'y'
            while newvals.answer == 'y':
                vals.append(input('Give a value the column should have:\n>'))
                newvals.prompt_valid('Add more values?')
            pickedcolumn = columns.validanswers[columns.answer]
            self.condcols[pickedcolumn] = tuple(vals)
            addmore.prompt_valid('Add more conditions?')



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
            self.pause = True
        elif answer == 'o':
            self.viewsavedsearches()
        elif answer == 'n':
            self.nuzhnosearch()
        elif answer == 'a':
            self.monoconc(True)
        elif answer == 'tme':
            self.monoconc(tme=True)
        elif answer == 'pc':
            self.pause=True
            self.Parconc()
        elif answer == 'cs':
            statmen = Statmenu()
            statmen.runmenu()

    def ListColumns(self):
        if not self.columns:
            psycon = psycopg(self.selecteddb,'juho')
            rows = psycon.FetchQuery('SELECT column_name FROM information_schema.columns WHERE table_name = %s',(Db.searched_table,))
            for idx, row in enumerate(rows):
                self.columns[str(idx)] = row[0]

class Statmenu:
    menuoptions = {'1':'Word count','c':'Return to main menu'}
    def __init__(self):
        self.menu = multimenu(Statmenu.menuoptions)
        self.menu.question = 'Select the function you would like to apply:'

    def wordCountForText(self, text_id, table):
        """Count the number of words in a given text and return it as a string"""
        query = 'SELECT count(*) from {} WHERE token NOT IN %(punct)s AND text_id = %(text_id)s'.format(table)
        res = Db.con.nondictquery(query,{'punct':tuple(string.punctuation),'text_id':text_id})
        return str(res[0][0])

    def CollectTexts(self):
        """Get a list of texts from the database"""
        return Db.con.dictquery('SELECT title, transtitle, id from text_ids')

    def WordCounts(self):
        """Count words in the texts"""
        #This needs to be improved:
        tables = {'source':'fi_conll','target':'ru_conll'}
        #########
        maxtitleLength = len('title')
        maxWcLength = len('word count')
        max_trtitleLength = len('translation title')
        max_trWcLength = len('trans. word count')
        texts = list()
        print('Analyzing...')
        #Start printing data for each text and target text
        results = self.CollectTexts()
        for res in results:
            #Fetch wordcount for each text and target text
            texts.append({'id':res['id'],'title':res['title'],'wordcount':self.wordCountForText(res['id'],tables['source']),
                'translation title':res['transtitle'],'trwordcount':self.wordCountForText(res['id'],tables['target'])})
            #Get string length information for the output table
            if len(res['title'])>maxtitleLength:
                maxtitleLength = len(res['title'])
            if len(texts[-1]['wordcount'])>maxWcLength:
                maxWcLength = len(texts[-1]['wordcount'])
            if len(res['transtitle'])>max_trtitleLength:
                max_trtitleLength = len(res['transtitle'])
            if len(texts[-1]['trwordcount'])>max_trWcLength:
                max_trWcLength = len(texts[-1]['trwordcount'])
        #Print the output table
        print('{0:3} | {1:{titlewidth}} | {2:{wcwidth}} | {3:{trtitlewidth}} | {4:{trwcwidth}}'.format('Id','Title','Word count', 'Translation title', 'translation wordcount',
            titlewidth = maxtitleLength, wcwidth = maxWcLength, trtitlewidth = max_trtitleLength, trwcwidth = max_trWcLength))
        for text in texts:
            print('{0:3} | {1:{titlewidth}} | {2:{wcwidth}} | {3:{trtitlewidth}} | {4:{trwcwidth}}'.format(text['id'],text['title'],text['wordcount'],text['translation title'],text['trwordcount'],
                titlewidth = maxtitleLength, wcwidth = maxWcLength, trtitlewidth = max_trtitleLength, trwcwidth = max_trWcLength))
        #Print csv if the user wants to:
        csvmenu = multimenu({'y':'yes','n':'no'}, 'Write csv?')
        if csvmenu.answer == 'y':
            with open('wordcounts.csv','w') as f:
                fieldnames = ['id', 'title','wordcount','translation title','trwordcount']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for text in texts:
                    writer.writerow(text)


    def runmenu(self):
        #Clear the terminal:
        os.system('cls' if os.name == 'nt' else 'clear')
        self.menu.prompt_valid()
        while self.menu.answer != 'c':
            self.evaluatestatmenu()
            self.menu.prompt_valid()

    def evaluatestatmenu(self):
        """choose what to do"""
        if self.menu.answer == '1':
            self.WordCounts()



##################################################

def printResults(thisSearch):
        if len(thisSearch.matches) >0:
            printcount = input('Found {} occurences. How many should I print? (press enter to print all)\n'.format(thisSearch.absolutematchcount))
            if printcount == '':
                printcount = thisSearch.absolutematchcount
            else:
                printcount = int(printcount)
            while printcount > thisSearch.absolutematchcount:
                printcount = int(input('Please give a number smaller than {}.'.format(thisSearch.absolutematchcount + 1)))
            ordermenu = multimenu({'r':'randomize','n':'Do not randomize'},'Should I randomize the order?')
            if ordermenu.answer =='r':
                randomkeys = random.sample(list(thisSearch.matches),printcount)
                printmatches = list()
                for rkey in randomkeys:
                    alignsegment = thisSearch.matches[rkey]
                    #randomly select 1 of the matches in this segment
                    printmatches.append(random.choice(alignsegment))
            else:
                printmatches = list()
                for align_id, matches in thisSearch.matches.items():
                    for match in matches:
                        if len(printmatches) < printcount:
                            printmatches.append(match)
                        else:
                            break
            #actual printing
            #========================================
            table = Texttable()
            #Initialize table printer
            table.set_cols_align(["l", "l"])
            table.set_cols_valign(["m", "m"])
            rows = list()
            for idx, match in enumerate(printmatches):
                match.BuildSlContext()
                if thisSearch.isparallel:
                    match.BuildTlContext()
                    rows.append(['Source text id: {}, Sentence id: {}, align id: {}\n'.format(match.matchedword.sourcetextid, match.matchedsentence.sentence_id, match.align_id), ''])
                    rows.append([get_color_string(bcolors.BLUE,match.slcontextstring), get_color_string(bcolors.RED,match.tlcontextstring)])
                else:
                    print('{}:\t{}\nSentence id: {}, align id: {}\n'.format(idx, match.matchedsentence.printstring, match.matchedsentence.sentence_id, match.align_id))
            if thisSearch.isparallel:
                table.add_rows(rows)
                print(table.draw() + "\n")
            #========================================
        else:
            print('Sorry, nothing found.')
            print(thisSearch.subquery)
            print(thisSearch.subqueryvalues)


def resultprinter(matchitems,limit=1,parallel=False):
    """Print to screen the specified number of elements from search object"""
    printed = 0
    sentences = dict()
    for key, matches in matchitems:
        for match in matches:
            if printed == int(limit):
                break
            #match.monoConcordance()
            #match.matchedsentence.buildPrintString()
            match.BuildSlContext()
            if  parallel:
                match.BuildTlContext()
            printed += 1
            print('{}:\t{}\nSentence id: {}, align id: {}\n'.format(printed,match.matchedsentence.printstring, match.matchedsentence.sentence_id, key))
            #Save the sentence so it can be referenced easily
            sentences[str(printed)] = match.matchedsentence
    return sentences

##################################################


#Start the menu

if __name__ == "__main__":
    searchmenu = MainMenu()
    while searchmenu.run == True:
        searchmenu.runmenu()
        if searchmenu.pause:
            input('Press enter to continue')
            searchmenu.pause=False
