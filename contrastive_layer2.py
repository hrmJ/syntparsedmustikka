#! /usr/bin/env python
import logging
import sys
from sqlalchemy import create_engine, update, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dbmodule import SqlaCon, mydatabase, psycopg
from search import Search, Match, Sentence, Word, ConstQuery, Db 
import contrastive_deptypes
 
dbname = 'syntparrus'
engine = create_engine('postgresql:///{}'.format(dbname), echo=False)
Base = declarative_base(engine)

class SnData(Base):
    """Access the SN analyzed data with sqlalchemy"""
    __tablename__ = 'ru_conll'
    __table_args__ = {'autoload':True}

def updateidlist(idlist,con):
    pass
    #con.insertquery("UPDATE fi_conll SET contr_deprel = NULL")

def createContrastiveLayer():
    """Creates the contrastive layer phase by phase"""
    prcon = psycopg('syntparrus','juho')
    pfcon = psycopg('syntparfin','juho')
    #contrastive_deptypes.sn_obj(prcon)
    #contrastive_deptypes.sn_gmod_own(prcon)
    contrastive_deptypes.sn_infcomp_from_predik(prcon)
    prcon.connection.commit()


#Start:
if __name__ == "__main__":

    #prcon = mydatabase('syntparrus','juho')
    #prcon.insertquery("UPDATE ru_conll SET contr_deprel = NULL WHERE contr_deprel IS NOT NULL")
    createContrastiveLayer()
