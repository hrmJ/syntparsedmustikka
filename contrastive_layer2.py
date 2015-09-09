#! /usr/bin/env python
import logging
import sys
from dbmodule import psycopg, mydatabase
from search import Search, Match, Sentence, Word, ConstQuery, Db 
from deptypetools import log
import sn
import tdt

def createContrastiveLayer(con):
    """Creates the contrastive layer phase by phase"""

    #SN:----------------------------------------
    #sn.gdep(con)
    #sn.obj(con)
    #sn.nsubj(con)
    #sn.nommod_own(con)
    #sn.advmod(con)
    #sn.infcomp(con)
    #sn.prtcl(con)
    #sn.prdctv(con)
    #sn.semsubj(con)
    #sn.cdep(con)
    #sn.agent(con)
    #sn.adpos(con)
    #sn.conj(con)
    #sn.attr(con)
    #sn.nommod(con)
    #TDT:----------------------------------------
    tdt.gdep(con)
    tdt.rel(con)
    tdt.obj(con)
    tdt.nsubj(con)
    tdt.nommod(con)
    tdt.advmod(con)
    tdt.infcomp(con)
    tdt.prtcl(con)
    tdt.prdctv(con)
    tdt.semsubj(con)
    tdt.cop(con)
    tdt.attr(con)
    tdt.cdep(con)
    tdt.conj(con)
    tdt.fixChains(con) # last

    # Commit:
    con.connection.commit()

if __name__ == "__main__":
    #Initialize a logger and start the function that creates the contrastive layer

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

    #Connect:
    prcon = psycopg('syntparrus','juho')
    pfcon = psycopg('syntparfin','juho')
    logging.info('\n{0} \nSTART CREATING THE CONTRASTIVE LAYER \n{0} \n'.format('*'*60))
    #logging.info('\n{0} \n The ParRus database \n{0} \n'.format('-'*60))
    #createContrastiveLayer(prcon)
    logging.info('\n{0} \n The ParFin database \n{0} \n'.format('-'*60))
    createContrastiveLayer(pfcon)
