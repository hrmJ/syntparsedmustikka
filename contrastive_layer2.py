#! /usr/bin/env python
import logging
import sys
from dbmodule import psycopg, mydatabase
from search import Search, Match, Sentence, Word, ConstQuery, Db 
import sn
 
class Featset:
    """Predefined feature sets and some methods to define them on the fly"""
    #REMEMBER  PRONONUNS
    def __init__(self):
        self.NounAcc =  self.createNounSet(cases = ('a',))
        self.NounDat =  self.createNounSet(cases = ('d',))
        self.PronAcc =  self.createPronSet(cases = ('a',))
        self.PronDat =  self.createPronSet(cases = ('d',))
        self.inf = ('Vmn----a-e','Vmn----a-p')
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

def LogNewDeprel(message):
    """Log the deprels name as header"""
    logging.info('{0}{1}{0}{2}{0}{1}{0}'.format('\n','='*50,message))

def log(message):
    """Log just a simple message"""
    logging.info(message)

def simpleupdate(thisSearch,dbcon, deprel):
    """In the prototypical case you just give the deprel of the contrastive layer"""
    logging.info('Updating {} items in the db'.format(len(thisSearch.listMatchids())))
    dbcon.query('UPDATE ru_conll SET contr_deprel = %(deprel)s WHERE id in %(idlist)s',{'deprel':deprel,'idlist':thisSearch.idlist})
    logging.info('to be updated: {} database rows.'.format(dbcon.cur.rowcount))

def makeSearch(ConditionColumns,database,dbtable,headcond=None,depcond=None):
    Db.searched_table = dbtable
    thisSearch = Search(database,askname=False)
    logging.info('Starting the search..')
    thisSearch = Search(database,askname=False)
    thisSearch.ConditionColumns.append(ConditionColumns)
    thisSearch.headcond = headcond
    thisSearch.depcond = depcond
    thisSearch.BuildSubQuery()
    thisSearch.find()
    logging.info('Search committed')
    return thisSearch

def createContrastiveLayer():
    """Creates the contrastive layer phase by phase"""
    prcon = psycopg('syntparrus','juho')
    pfcon = psycopg('syntparfin','juho')
    #sn.gdep(prcon)
    #sn.obj(prcon)
    #sn.gmod_own(prcon)
    #sn.infcomp(prcon)
    #sn.prtcl(prcon)
    sn.prdctv(prcon)
    #sn.semsubj(prcon)
    #sn.cdep(prcon)
    #sn.conj(prcon)
    #sn.attr(prcon)
    prcon.connection.commit()

#Start:
if __name__ == "__main__":

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

    #prcon = mydatabase('syntparrus','juho')
    #prcon.insertquery("UPDATE ru_conll SET contr_deprel = NULL, contr_head = NULL")
    createContrastiveLayer()
