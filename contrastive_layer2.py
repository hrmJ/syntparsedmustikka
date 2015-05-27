#! /usr/bin/env python
import logging
import sys
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dbmodule import SqlaCon
from search import Search, Match, Sentence, Word, ConstQuery, Db 
 
engine = create_engine('postgresql:///syntparrus', echo=False)
Base = declarative_base(engine)

class SnData(Base):
    """Access the SN analyzed data"""
    __tablename__ = 'sn_sandbox'
    __table_args__ = {'autoload':True}
 
class Featset:
    """Includes predefined feature sets"""
    facc = ('','')
    pass


def createContrastiveLayer():
    """Creates the contrastive layer phase by phase"""
    #1. Create the category of object
    thisSearch = Search(self.selecteddb)
    thisSearch.ConditionColumns.append({'feat':('Ncfsan','Npfsan'),'deprel':('kompl-1',)})
    #con = SqlaCon(Base, engine)
    #con.LoadSession()

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

