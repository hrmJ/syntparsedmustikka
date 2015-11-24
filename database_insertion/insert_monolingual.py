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
        insert_pair.InsertPair(dbname,slfile,sl_tablename=sl_tablename)
    except IndexError:
        raise insert_pair.ArgumentError('Usage: {} <database name> <sl file> <source language>'.format(sys.argv[0]))
