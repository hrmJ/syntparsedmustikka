#! /usr/bin/env python
#Import modules
import codecs
import csv
import os
import sys
from collections import defaultdict
from lxml import etree
import string
import re
#local modules
from dbmodule import mydatabase, SqlaCon
from menus import Menu, multimenu, yesnomenu 
from search import Search, Match, Sentence, Word, ConstQuery, Db 
import itertools
from sqlalchemy import create_engine, ForeignKey, and_
from sqlalchemy import Column, Date, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref, sessionmaker
import logging
import time

engine = create_engine('postgresql:///{}'.format('postprocess'), echo=False)
Base = declarative_base(engine)

class Fidconst(Base):
    """Query and insert to the fi_dupl_constfix database table"""

    __tablename__ = 'fi_dupl_constfix'

    id = Column(Integer, primary_key=True)
    criterionattr = Column(String)  
    criterionval = Column(String)  
    launcherword = Column(Integer)
    reject = Column(Integer)

class Fidcoll(Base):
    """Query and insert to the fi_dupl_constfix_collocates database table"""

    __tablename__ = 'fi_dupl_constfix_collocates'

    id = Column(Integer, primary_key=True)
    launcher_id = Column(Integer, ForeignKey("fi_dupl_constfix.id"))
    Fidconst = relationship("Fidconst", backref=backref("fi_dupl_constfix_collocates", order_by=id))
    criterionattr = Column(String)  
    criterionval = Column(String)  
    collocate_id = Column(Integer)  


class RejectDepHead(Base):
    """Query and insert to the reject_dep_head database table"""

    __tablename__ = 'reject_dep_head'

    id = Column(Integer, primary_key=True)
    criterionattr = Column(String)  
    criterionval = Column(String)  
    reject = Column(Integer)

class RejectDepArg(Base):
    """Query and insert to the reject_dep_arg database table"""

    __tablename__ = 'reject_dep_arg'

    id = Column(Integer, primary_key=True)
    head_id = Column(Integer, ForeignKey("reject_dep_head.id"))
    RejectDepHead = relationship("RejectDepHead", backref=backref("reject_dep_arg", order_by=id))
    criterionattr = Column(String)  
    criterionval = Column(String)  
    #Will this be a rejection or acception based rule
    action = Column(String)

class PotentialDuplicatePair:

    def __init__(self,matchlist):

        self.reason = 'Rejected as a duplicate'
        self.matchlist = matchlist
        self.sentences = dict()
        for idx, match in enumerate(self.matchlist):
            match.BuildSentencePrintString()
            self.sentences[str(idx)] = match.matchedsentence.printstring

    def select(self):
        """Decide wich duplicate to reject and make rules based on the decision"""
        answers = dict()
        answers['n'] = 'none'
        answers['q'] = 'quit'
        #Build the question
        answers.update(self.sentences)
        selmenu = multimenu(answers)
        selmenu.prompt_valid('Which one will you reject?')
        if selmenu.answer == 'q':
            return False
        self.rejected = selmenu.answer
        self.evalueatesel()
        return True

    def evalueatesel(self):
        """Evaluate the decision about rejection"""
        if self.rejected == 'a':
            for idx, match in enumerate(self.matchlist):
                match.postprocess('')
        else:
            #If something is rejected
            for idx, match in enumerate(self.matchlist):
                if str(idx) == str(self.rejected):
                   #If this is the user's choice, reject it
                   match.postprocess(self.reason)
                else:
                   #otherwise, just mark this processed
                   match.postprocess('')

    def CreateRejectionRule(self):
        #Connect to the postproseccing database
        con = SqlaCon(Base, engine)
        rule = Fidconst()
        rule.fi_dupl_constfix_collocates = list()
        collocatecandidates = dict()
        #The menu:
        selmenu = multimenu(self.sentences)
        selmenu.prompt_valid('Which word is the launcher?')
        #Iterate:
        for idx, match in enumerate(self.matchlist):
            if str(idx) == selmenu.answer:
               #If this is the user's choice, make it the launcher
               rule.launcherword = idx
               launcher = match.matchedword
            else:
                #if note, make them collocates
                collocatecandidates[idx]=match.matchedword
        #Build the part of the rule that concerns the launcher
        setRuleAttributes(rule,launcher)
        rule.reject = self.rejected
        #Build the part of the rule that concerns collocates
        for idx, collocate in collocatecandidates.items():
            sign = yesnomenu()
            sign.prompt_valid('Is this collocate significant in constructing the rule?: <{}>'.format(collocate.token))
            if sign.answer == 'y':
                rule.fi_dupl_constfix_collocates.append(Fidcoll())
                setRuleAttributes(rule.fi_dupl_constfix_collocates[-1],collocate)
                rule.fi_dupl_constfix_collocates[-1].collocate_id = idx
        #Insert to db
        con.insert(rule)

    def CheckExistingRules(self):
        """Query the postprocess database to find rules that already exist"""
        con = SqlaCon(Base, engine)
        con.LoadSession()
        matchcategories = dict()
        for launcher_id, match in enumerate(self.matchlist):
            #1. Find the launcher
            lword = match.matchedword
            matchcategories['token'] = con.session.query(Fidconst).filter(Fidconst.launcherword == launcher_id).filter(Fidconst.criterionattr == 'token').filter(Fidconst.criterionval == lword.token).first()
            matchcategories['lemma'] = con.session.query(Fidconst).filter(Fidconst.launcherword == launcher_id).filter(Fidconst.criterionattr == 'lemma').filter(Fidconst.criterionval == lword.lemma).first()
            matchcategories['feat']  = con.session.query(Fidconst).filter(Fidconst.launcherword == launcher_id).filter(Fidconst.criterionattr == 'feat').filter(Fidconst.criterionval == lword.feat).first()
            matchcategories['pos']   = con.session.query(Fidconst).filter(Fidconst.launcherword == launcher_id).filter(Fidconst.criterionattr == 'pos').filter(Fidconst.criterionval == lword.pos).first()
            logging.info('Checking word {}(id={}) as a launcher'.format(lword.token,launcher_id))
            for category, res in matchcategories.items():                                                                                                                                     
                if res:
                    #if a value pair (e.g. criterion atrr= lemma and word.lemma = criterionval and launcherword = this words idx) matched
                    collocates = self.matchlist[:launcher_id] + self.matchlist[launcher_id+1:]
                    #If not enough collocates, then quit
                    collocate_rules = con.session.query(Fidcoll).filter(Fidcoll.launcher_id == res.id).all()
                    crule_log = ''
                    if len(collocates) >= len(collocate_rules) and collocate_rules:
                        allcollocatesmatch = True
                        collocatematched = False
                        for collocate_id, collocate in enumerate(self.matchlist):
                            cword = collocate.matchedword
                            if collocate_id != launcher_id:
                                logging.info('{}:{}'.format(collocate_id,cword.token))
                                #For every word that is different from the one used as a launcher:Fidcoll.
                                logging.info('Trying qyery:resid={},launcher_id={}'.format(res.id,launcher_id))
                                vals = con.session.query(Fidcoll.criterionattr,Fidcoll.criterionval).filter(Fidcoll.launcher_id == res.id).filter(Fidcoll.collocate_id == collocate_id).first()
                                if vals:
                                    #If there was a rule concerning this collocate but this collocate doesn't match it
                                    crule_log += 'collocate number {}: {} = {}'.format(collocate_id,vals.criterionattr,vals.criterionval)
                                    if getattr(cword,vals.criterionattr) != vals.criterionval:
                                        allcollocatesmatch = False
                                    else:
                                        collocatematched = True
                        if allcollocatesmatch and collocatematched:
                            #If all collocates matched, there was a rule and it will be applied
                            self.rejected = res.reject
                            self.evalueatesel()
                            logging.info('''\nApplied a rule\n==================\nSentences:\n    {}\nLauncher word: {}\nLauncherwords criteria {} = {}\n{}\nRejected: {}'''.format('\n    '.join(list(self.sentences.values())), launcher_id, category,getattr(lword,category),crule_log,res.reject))
                            return True


class PotetialNontemporal:
    """THis is for dealing with potentially non-temporal ones"""

    def __init__(self,match):

        self.reason = 'Rejected as non-temporal'
        self.match = match
        match.BuildSentencePrintString()
        self.sentence  = match.matchedsentence.printstring
        self.hlheadsentence = match.matchedsentence.Headhlprintstring
        #Information about head and dependent words
        self.head = self.match.matchedsentence.words[self.match.matchedword.head]
        self.dependent = self.match.matchedword
        self.subdependents = self.match.matchedsentence.listDependents(self.dependent.tokenid)

    def CheckExistingRules(self):
        """Query the postprocess database to find rules that already exist"""
        con = SqlaCon(Base, engine)
        con.LoadSession()
        matchcategories = dict()
        matchcategories['token'] = con.session.query(RejectDepHead).filter(RejectDepHead.criterionattr == 'token').filter(RejectDepHead.criterionval == self.head.token).first()
        matchcategories['lemma'] = con.session.query(RejectDepHead).filter(RejectDepHead.criterionattr == 'lemma').filter(RejectDepHead.criterionval == self.head.lemma).first()
        matchcategories['feat'] = con.session.query(RejectDepHead).filter(RejectDepHead.criterionattr == 'feat').filter(RejectDepHead.criterionval == self.head.feat).first()
        matchcategories['pos'] = con.session.query(RejectDepHead).filter(RejectDepHead.criterionattr == 'pos').filter(RejectDepHead.criterionval == self.head.pos).first()
        logging.info('Checking word {} as head'.format(self.head.token))
        for category, res in matchcategories.items():                                                                                                                                     
            if res:
                vals = con.session.query(RejectDepArg).filter(RejectDepArg.head_id == res.id).first()
                if getattr(self.dependent,vals.criterionattr) == vals.criterionval:
                    logging.info("""\nApplied a rule\n==================\nSentence\n    {}\nHead: {}\nHead's criteria {} = {}\nAction: {}\nDependent's criteria: {} = {}\n
                                """.format(self.sentence, self.head.token, category, getattr(self.head,category), vals.action,vals.criterionattr,getattr(self.dependent,vals.criterionattr)))
                    if vals.action == 'a':
                        self.rejected = 'n'
                    elif vals.action == 'r':
                        self.rejected = 'y'
                    self.evalueatesel()
                    return True
        #If no match, return false
        return False


    def select(self):
        """Decide to reject or not and make rules based on the decision"""
        self.match.BuildSentencePrintString()
        print('{0}{1}{0}'.format('\n'*2,self.hlheadsentence))
        selmenu = multimenu({'y' : 'yes, REJECT this!', 'n' : 'no, ACCEPT this', 'q' : 'quit'})
        selmenu.prompt_valid('Should I REJECT this match?')
        if selmenu.answer == 'q':
            return False
        else:
            self.rejected = selmenu.answer
            self.evalueatesel()
            return True

    def evalueatesel(self):
        """Evaluate the decision about rejection"""
        if self.rejected == 'n':
                   self.match.postprocess('')
        elif self.rejected == 'y':
                   self.match.postprocess(self.reason)

    def CreateRule(self):
        #Connect to the postproseccing database
        con = SqlaCon(Base, engine)
        headrule = RejectDepHead()
        headrule.reject_dep_arg = [RejectDepArg()]
        #Set the rule attributes
        setRuleAttributes(headrule,self.head)
        setRuleAttributes(headrule.reject_dep_arg[-1],self.dependent)
        #Mark, whether this is an accepting or rejecting rule
        if self.rejected == 'n':
            headrule.reject_dep_arg[-1].action = 'a'
        elif self.rejected == 'y':
            headrule.reject_dep_arg[-1].action = 'r'
        ##Insert to db
        con.insert(headrule)

def setRuleAttributes(rule, word):
    """Ask the user about which attributes with what value defines the rule"""
    word.printAttributes()
    selmenu = multimenu({'0':'token', '1':'lemma', '2':'feat', '3':'pos'})
    selmenu.prompt_valid('Which attribute is the criterion?')
    rule.criterionattr = selmenu.validanswers[selmenu.answer]
    rule.criterionval = getattr(word,rule.criterionattr)

def FilterDuplicates1(thisSearch):
    """Process matches with the same head and throw away the other"""
    logging.info('*'*150)
    #Arrange the matches in a dict that has the matched word's head's database id as its key
    matchitems = sorted(thisSearch.matches.items())
    mheadids = dict()
    mheadids = defaultdict(list)
    for key, matches in matchitems:
        for match in matches:
            mword = match.matchedword
            if not match.postprocessed:
                #If this match has not yet been processed
                mheadids[match.matchedsentence.words[mword.head].dbid].append(match)
    #Just for counting:
    total = 0
    for mheadid, matchlist in mheadids.items():
        if len(matchlist)>1:
            total += 1
    processed = 0
    #Iterate through the dict and process all the instances where one headid has multiple matches
    for mheadid, matchlist in mheadids.items():
        if len(matchlist)>1:
            processed += 1
            thisPair = PotentialDuplicatePair(matchlist)
            if not thisPair.CheckExistingRules():
                #If no predefined rules exist
                #Clear the output for conveniance
                os.system('cls' if os.name == 'nt' else 'clear')
                print('Processing duplicate no {}/{}'.format(processed,total))
                cont = thisPair.select()
                if not cont:
                    break
                if thisPair.rejected != 'n':
                    #If something was rejected, ask about a rule:
                    createrule = yesnomenu()
                    createrule.prompt_valid('Create a rule?')
                    if createrule.answer =='y':
                        thisPair.CreateRejectionRule()

def FilterNonTemporal(thisSearch):
    """Process matches and reject the ones that by your interpretation are not temporal"""
    logging.info('Filtering NON-TEMPORAL: ' + '*'*150)
    matchestoprocess = list()
    # Count how much is to be processed and exlcude those that already are
    for key, matches in thisSearch.matches.items():
        for match in matches:
            if not match.postprocessed:
                #If this match has not yet been processed
                matchestoprocess.append(match)
    processed = 0
    for match in matchestoprocess:
        processed += 1
        thismatch = PotetialNontemporal(match) 
        if not thismatch.CheckExistingRules():
            #If no predefined rules exist
            #Clear the output for conveniance
            os.system('cls' if os.name == 'nt' else 'clear')
            print('Processing match no {}/{}'.format(processed,len(matchestoprocess)))
            cont = thismatch.select()
            if not cont:
                return 'Remember to save, if necessary'
            else:
                #If something was rejected, ask about a rule:
                createrule = yesnomenu()
                createrule.prompt_valid('Create a rule?')
                if createrule.answer =='y':
                    thismatch.CreateRule()

def printprocessed(searcho):
    for key, matches in searcho.matches.items():
        for match in matches:
            if match.postprocessed:
                match.BuildSentencePrintString()
                print('{}: {}\n\n'.format(match.rejectreason,match.matchedsentence.printstring))

#====================================================================================================
#Initialize a logger
root = logging.getLogger()
root.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s: %(message)s')
fh = logging.FileHandler('logof_filtermatches.txt',mode='w')
fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)
root.addHandler(fh)

Base.metadata.create_all(engine)


