#! /usr/bin/env python
from dbmodule import psycopg
import csv

def InsertDeprelColumns(lang):

    con = psycopg('results','juho')
    tablename = lang + '_' + 'deprels'
    #List what already is in the db as a column
    column_names = con.FetchQuery("SELECT column_name FROM information_schema.columns WHERE table_name = %(tablename)s",{'tablename':tablename})
    existingcolumns = list()
    for column_name in column_names:
        existingcolumns.append(column_name[0])

    #create the columns, if they don't exist
    if lang == 'ru':
        sndeps = ListSnDeprels()
        for sndep in sndeps:
            colname = 'dr_' +  sndep.replace('-','_')
            if  colname.lower() not in existingcolumns:
                con.query('ALTER TABLE {} ADD COLUMN {} VARCHAR'.format(tablename, colname.lower()))
    con.connection.commit()



def ListSisters(mword, clause, lang, row):
    #first, get the row names according to language
    if lang == 'ru':
        sndeps = ListSnDeprels()
        for sndep in sndeps:
            colname = 'dr_' + sndep.replace('-','_')
            row[colname] = 0
    #then count, how many of each deprel present in sister words
    try:
        mword.headword.ListDependents(clause)
        for sister in mword.headword.dependentlist:
            colname = 'dr_' + sister.deprel.replace('-','_')
            row[colname] += 1
    except AttributeError:
        pass
    
    return row



def ListSnDeprels():
    """List the original dependency relations of SN"""
    sndeps = list()
    with open("/home/juho/phdmanuscript/data/parrusdeprel.csv", 'r') as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            sndeps.append(row[0])
    return sndeps
