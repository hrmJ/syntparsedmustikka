#! /usr/bin/env python
import logging
import sys
from dbmodule import psycopg, mydatabase
from search import Search, Match, Sentence, Word, ConstQuery, Db 
import sn
import tdt

def createContrastiveLayer():
    """Creates the contrastive layer phase by phase"""

    prcon = psycopg('syntparrus','juho')
    pfcon = psycopg('syntparfin','juho')
    #sn.gdep(prcon)
    #sn.obj(prcon)
    #sn.nsubj(prcon)
    #sn.nommod_own(prcon)
    #sn.infcomp(prcon)
    #sn.prtcl(prcon)
    #sn.prdctv(prcon)
    #sn.semsubj(prcon)
    #sn.cdep(prcon)
    #sn.conj(prcon)
    #sn.attr(prcon)
    #sn.nommod(prcon)
    #tdt.gdep(prcon)
    #tdt.obj(prcon)
    #tdt.infcomp(prcon)
    #tdt.semsubj(prcon)
    #tdt.advmod(prcon)
    #tdt.prdctv(prcon)
    tdt.nsubj(prcon)
    #tdt.cop(prcon)
    #tdt.prtcl(prcon)
    #tdt.attr
    #tdt.cdep
    #tdt.conj
    #tdt.fixChains(prcon) # last

    prcon.connection.commit()

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

    createContrastiveLayer()
