#! /usr/bin/env python
import logging
import sys
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dbmodule import SqlaCon
from search import Search, Match, Sentence, Word, ConstQuery, Db 
from contrastive_layer2 import dbname

class Featset:
    """Predefined feature sets and some methods to define them on the fly"""
    #REMEMBER  PRONONUNS
    def __init__(self):
        self.NounAcc =  self.createNounSet(cases = ('a',))
        self.NounDat =  self.createNounSet(cases = ('d',))
        self.PronAcc =  self.createPronSet(cases = ('a',))
        #Pronouns


    def createNounSet(self,pos = 'N', nountypes = ('c','p'), genders = ('m','f','n'), numbers = ('s','p'), cases = ('n','g','a','i','d','l'), animacies = ('n','y')):
       """ Create tuples with all the specified feats"""
       items = self.additemlist([pos],nountypes)
       items = self.additemlist(items,genders)
       items = self.additemlist(items,numbers)
       items = self.additemlist(items,cases)
       items = self.additemlist(items,animacies)
       return tuple(items)

    def createPronSet(self,pos = 'P-', person = ('1','2','3','-'), genders = ('m','f','n','-'), numbers = ('s','p','-'), cases = ('n','g','a','i','d','l','-'), postype = ('n','a','r')):
       """ Create tuples with all the specified feats"""
        #P-3msin
       items = self.additemlist([pos],person)
       items = self.additemlist(items,genders)
       items = self.additemlist(items,numbers)
       items = self.additemlist(items,cases)
       items = self.additemlist(items,postype)
       return tuple(items)

    def additemlist(self, oldvalues, newvalues):
        """Create a list with all the combinations of the supplied values"""
        newitems = list()
        for oldvalue in oldvalues:
            for newvalue in newvalues:
                newitems.append(oldvalue + newvalue)
        return newitems

########################################################################################################################

def sn_obj(dbcon=False):
    """"Create the category of obj in SN"""
    featset = Featset()
    logging.info('='*50 + '\n' + '1. Create the category of object in the SN data')
    Db.searched_table = 'ru_conll'
    thisSearch = makeSearch(database='syntparrus', ConditionColumns={'feat':featset.NounAcc,'deprel':('1-компл',)}, headcond = {'column':'pos','values':('V',)})
    logging.info('Updating {} items in the db'.format(len(thisSearch.listMatchids())))
    dbcon.query('UPDATE ru_conll SET contr_deprel = %(deprel)s WHERE id in %(idlist)s',{'deprel':'obj','idlist':thisSearch.idlist})
    logging.info('to be updated: {} database rows.'.format(dbcon.cur.rowcount))

def sn_gmod_own(dbcon=False):
    """"Create the category of gmod_own in SN
    NEEDS ADJUSTMENTS, Something's probably being left out 
    ------------------------------
    """
    featset = Featset()
    logging.info('='*50 + '\n' + '1. Create the category of gmod_own in the SN data')
    Db.searched_table = 'ru_conll'
    thisSearch = makeSearch(database='syntparrus', ConditionColumns={'token':('у',),'deprel':('1-компл',)}, headcond = {'column':'lemma','values':('быть','есть', 'бывать', 'нет','мало','много')})
    logging.info('Updating {} items in the db'.format(len(thisSearch.listMatchids())))
    dbcon.query('UPDATE ru_conll SET contr_deprel = %(deprel)s WHERE id in %(idlist)s',{'deprel':'gmod-own','idlist':thisSearch.idlist})
    logging.info('to be updated: {} database rows.'.format(dbcon.cur.rowcount))

def sn_infcomp_from_predik(dbcon=False):
    """Muokkaan kontrastiivista analyysikerrosta varten SN-analyysiä siten, että
    verbillä ilmaistavat subjektit
    luokitellaan uudella tunnisteella infcomp"""
    logging.info('='*50 + '\n' + '1. Make infinitive subjects of SN infcomps')
    Db.searched_table = 'ru_conll'
    thisSearch = makeSearch(database='syntparrus', ConditionColumns={'deprel':('предик',),'pos':('V',),'feat':('Vmn----a-e','Vmn----a-p')})
    logging.info('Updating {} items in the db'.format(len(thisSearch.listMatchids())))
    dbcon.query('UPDATE ru_conll SET contr_deprel = %(deprel)s WHERE id in %(idlist)s',{'deprel':'infcomp','idlist':thisSearch.idlist})
    logging.info('to be updated: {} database rows.'.format(dbcon.cur.rowcount))

def sn_semsubj(dbcon=False):
    """Otan käyttöön termin semsubj nesessiivilauseille ja muille vastaaville rakenteille, joissa SN-analyysi
    määrittää infinitiivimuotoisen verbin subjektiksi. Näin TDT:n nsubj ja SN:n
    2-kompl ja dat-subj muuttuvat (näiden lauseiden osalta) kontrastiivisessa
    kerroksessa muotoon semsubj.
    
    Rakenteen finiittimuotoinen verbi katsotaan
    SN-jäsennyksen mukaisesti juureksi ja infinitiivimuotoinen verbi luetaan infcomp-kategoriaan.
    
    Muutan kuitenkin SN-jäsennystä TDT-jäsennyksen mallin mukaiseksi siinä,
    että semsubj-kategorialla analysoitu sanamuoto katsotaan infinitiivimuodon
    eikä apuverbin dependentiksi."""

    featset = Featset()
    thisSearch = makeSearch(database='syntparrus', ConditionColumns={'deprel':('2-компл','дат-субъект')})
    SemSubjIds = list()
    #! >>
    SemsubjHeadids = list()
    #Check out whether there is a 'predik' depending on the verbal head
    for matchlist in thisSearch.matches.items():
        for match in matchlist:
            match.matchedsentence.listDependents(match.matchedword.head)
            for codependent in match.matchedsentence.dependentlist:
                #If there is a verbal codependent marked as predik AND the nominal complement is in dative:
                if (codependent.deprel == 'предик' and condependent.pos='V') and match.feat in featset.NounDat:
                    SemSubjIds.append(match.matchedword.dbid)
                    SemsubjHeadids.append(match.matchedword.dbid)
    logging.info('Updating {} items in the db'.format(len(SemSubjIds)))
    dbcon.query('UPDATE ru_conll SET contr_deprel = %(deprel)s WHERE id in %(idlist)s',{'deprel':'semsubj','idlist':SemSubjIds})
    logging.info('to be updated: {} database rows.'.format(dbcon.cur.rowcount))

########################################################################################################################

def makeSearch(ConditionColumns,database,headcond=None,depcond=None):
    thisSearch = Search(database,askname=False)
    logging.info('Starting the search..')
    thisSearch = Search(dbname,askname=False)
    thisSearch.ConditionColumns.append(ConditionColumns)
    thisSearch.headcond = headcond
    thisSearch.depcond = depcond
    thisSearch.BuildSubQuery()
    thisSearch.find()
    logging.info('Search committed')
    return thisSearch

########################################################################################################################
#Initialize a logger

root = logging.getLogger()
root.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s: %(message)s')

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)

fh = logging.FileHandler('logof_contrastivelayer.txt')
fh.setLevel(logging.DEBUG)

fh.setFormatter(formatter)
ch.setFormatter(formatter)
root.addHandler(fh)
root.addHandler(ch)
