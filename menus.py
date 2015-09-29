#! /usr/bin/env python
#Classes{{{1
#Menu{{{2
from texttable import Texttable, get_color_string, bcolors
import os

class Menu:
    """Any command line menus that are used to ask the user for input"""
    def prompt_valid(self,definedquestion=''):
            try:
                if self.clearscreen:
                    os.system('cls' if os.name == 'nt' else 'clear')
            except AttributeError:
                pass
            if definedquestion:
                self.question = definedquestion
            if len(self.validanswers) > 10 and 'n' not in self.validanswers and 'nn' not in self.validanswers:
                dontchangequestion=False
                #If there are lots of options, arrange them in columns:
                colcount = 0
                optioncols = list()
                table = Texttable()
                optioncols.append('')
                colaligns = ["l"]
                answerkeys = sorted(map(int,self.validanswers))
                for answer in answerkeys:
                    value = self.validanswers[str(answer)]
                    colcount += 1
                    optioncols[-1] += '{}:{}\n'.format(answer,value)
                    if colcount == 10:
                        colcount = 0
                        optioncols.append('')
                        colaligns.append("l") 
                table.set_cols_align(colaligns)
                table.add_rows([optioncols])
                print(table.draw() + "\n")
                if not dontchangequestion:
                    question = self.question + "\n>"
            else:
                #Make a printable string from the dict:
                options = '\n                '.join("{!s}: {!s}".format(key,val) for (key,val) in sorted(self.validanswers.items()))
                question = "{}\n{}{}\n>".format(self.question,'                ',options)
            self.answer=input(question)
            while self.answer not in self.validanswers.keys():
                self.answer = input("Please give a valid answer.\n {}".format(question))
            return self.answer

    def prompt(self,definedquestion=''):
            if definedquestion:
                self.question = definedquestion
            #Make a printable string from the dict:
            options = '\n                '.join("{!s}: {!s}".format(key,val) for (key,val) in sorted(self.validanswers.items()))
            question = "{}\n{}{}\n>".format(self.question,'                ',options)
            self.answer=input(question)

    def redifine_and_prompt(self, newquestion, newanswers):
        self.question = newquestion
        self.validanswers = newanswers
        self.prompt_valid()
        return self.answer

class yesnomenu(Menu):
    validanswers = { 'y':'yes','n':'no' }

class multimenu(Menu):
    def __init__(self, validanswers, promptnowquestion='', clearscreen=True):
        self.validanswers=validanswers
        self.clearscreen = clearscreen
        if promptnowquestion:
            self.question = promptnowquestion
            self.prompt_valid()


