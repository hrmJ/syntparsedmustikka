#! /usr/bin/env python
import sys
import os
from dbmodule import psycopg
from progress.bar import Bar
import re
from insert_translation import MissingTextError, AlignMismatch
import insert_pair

if __name__ == "__main__":
    try:
        dbname = sys.argv[1]
        slfile = sys.argv[2]
        sl_tablename = sys.argv[3] + '_conll'
        reference_file = sys.argv[4]
        insert_pair.InsertPair(dbname,slfile,sl_tablename=sl_tablename, reference_file=reference_file)
    except IndexError:
        #import ipdb; ipdb.set_trace()
        raise insert_pair.ArgumentError('Usage: {} <database name> <sl file> <source language> <reference file>'.format(sys.argv[0]))
