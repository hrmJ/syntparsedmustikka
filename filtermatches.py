#! /usr/bin/env python
#Import modules
import codecs
import csv
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
                if str(idx) == self.rejected:
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
        for idx, match in enumerate(self.matchlist):
            #1. Find the launcher
            word = match.matchedword
            # Fetch everything where the launcher is the sameth element
            launcherids = con.session.query(Fidconst.id).filter(Fidconst.launcherword == idx).all()
            launcherids = flattenids(launcherids)
            # Fetch all the attribute-value pairs of those rules
            avpairs = con.session.query(Fidconst.criterionattr,Fidconst.criterionval,Fidconst.id).filter(Fidconst.id.in_(launcherids)).all()
            for avpair in avpairs:
                #if this word is a launcher and there is a rule with some of this word's attributes matching it:
                if getattr(match.matchedword,avpair.criterionattr) == avpair.criterionval:
                    for idx2, match2 in enumerate(self.matchlist):
                        #other words of the duplicatepair
                        if idx2 != idx:
                            # Fetch everything where the collocate is the sameth element
                            collocateids = con.session.query(Fidcoll).filter(Fidcoll.collocate_id == idx2).all()
                            collocateids = flattenids(collocateids)
                            # Fetch all the attribute-value pairs of those rules
                            collocate_avpairs = con.session.query(Fidcoll.criterionattr,Fidcoll.criterionval,Fidcoll.id).filter(Fidcoll.id.in_(collocateids)).all()
                            for collocate_avpair in collocate_avpairs:
                                #if this word is a launcher and there is a rule with some of this word's attributes matching it:
                                if getattr(self.matchlist[idx2].matchedword,collocate_avpair.criterionattr) == collocate_avpair.criterionval:
                                    print('{}:{}'.format(avpair.criterionattr,avpair.criterionval))
                                    print('{}:{}'.format(collocate_avpair.criterionattr,collocate_avpair.criterionval))
                                    print('FOUNDIT!!')
                                    break

            #res = con.session.query(Fidconst).filter(and_(Fidconst.launcherword == idx,
            #                                              Fidconst.criterionattr == getattr(word, Fidconst.criterionattr),
            #                                              Fidconst.criterionval == getattr(word, Fidconst.criterionval)
            #                                              )).first()


def setRuleAttributes(rule, word):
    """Ask the user about which attributes with what value defines the rule"""
    word.printAttributes()
    selmenu = multimenu({'0':'token', '1':'lemma', '2':'feat', '3':'pos'})
    selmenu.prompt_valid('Which attribute is the criterion?')
    rule.criterionattr = selmenu.validanswers[selmenu.answer]
    rule.criterionval = getattr(word,rule.criterionattr)

def FilterDuplicates1(thisSearch):
    """Process matches with the same head and throw away the other"""
    #Arrange the matches in a dict that has the matched word's head's database id as its key
    matchitems = sorted(thisSearch.matches.items())
    mheadids = dict()
    mheadids = defaultdict(list)
    for key, matches in matchitems:
        for match in matches:
            mword = match.matchedword
            mheadids[match.matchedsentence.words[mword.head].dbid].append(match)
    #Iterate through the dict and process all the instances where one headid has multiple matches
    for mheadid, matchlist in mheadids.items():
        if len(matchlist)>1:
            thisPair = PotentialDuplicatePair(matchlist)
            thisPair.CheckExistingRules()
            cont = thisPair.select()
            if not cont:
                break
            if thisPair.rejected != 'n':
                #If something was rejected, ask about a rule:
                createrule = yesnomenu()
                createrule.prompt_valid('Create a rule?')
                if createrule.answer =='y':
                    thisPair.CreateRejectionRule()


def printprocessed(searcho):
    for key, matches in searcho.matches.items():
        for match in matches:
            if match.postprocessed:
                match.BuildSentencePrintString()
                print('{}: {}\n\n'.format(match.rejectreason,match.matchedsentence.printstring))

def flattenids(idlist):
    flatlist = list()
    for iditem in idlist:
        flatlist.append(iditem.id)
    return flatlist


#Base.metadata.create_all(engine)
