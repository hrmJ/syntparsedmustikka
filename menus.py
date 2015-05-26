#! /usr/bin/env python
#Classes{{{1
#Menu{{{2

class Menu:
    """Any command line menus that are used to ask the user for input"""
    def prompt_valid(self,definedquestion=''):
            if definedquestion:
                self.question = definedquestion
            #Make a printable string from the dict:
            options = '\n                '.join("{!s}: {!s}".format(key,val) for (key,val) in sorted(self.validanswers.items()))
            question = "{}\n{}{}\n>".format(self.question,'                ',options)
            self.answer=input(question)
            while self.answer not in self.validanswers.keys():
                self.answer = input("Please give a valid answer.\n {}".format(question))

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
    def __init__(self, validanswers, promptnowquestion=''):
        self.validanswers=validanswers
        if promptnowquestion:
            self.question = promptnowquestion
            self.prompt_valid()


