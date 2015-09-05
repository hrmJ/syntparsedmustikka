#! /usr/bin/env python
import csv
import sys
import re
from dbmodule import psycopg
from insertconll_first_todb_bangs import GetLastValue, TrimList
from progress.bar import Bar

class MissingTextError(Exception):
    pass

class AlignMismatch(Exception):
    pass

def main():
    #Get command line input:
    try:
        conllinputfile = sys.argv[1]
        text_id = sys.argv[2]
        dbname = sys.argv[3]
        sl_dbtablename = sys.argv[4]
        tl_dbtablename = sys.argv[5]
    except:
        print('''Usage: {} 
        <path to target language conll formatted text>
        <text id of the inserted source language text>
        <database name>
        <source language database table name>
        <target language database table name>
        '''.format(sys.argv[0]))
        sys.exit(0)

    #Connect to the database
    con = psycopg(dbname,'juho')
    #read the conll data
    with open(conllinputfile, 'r') as f:
        conllinput = f.read()

    #fetch the id of the pair that is already inserted
    text_id = con.FetchQuery("SELECT id FROM {} WHERE id = %s".format('text_ids'),(text_id,))
    try:
        text_id = text_id[0][0]
    except IndexError:
        raise MissingTextError('No such id in the text_ids table')

    #Get all the align ids that were inserted with the first file
    align_ids = con.FetchQuery("SELECT DISTINCT align_id FROM {} WHERE text_id = %s order by align_id".format(sl_dbtablename),(text_id,))

    # Split the translation file into aligned segments according to the !!!! -notation
    splitpattern = re.compile(r"\d+\t![^\n]+\n\n?\d+\t![^\n]+\n\n?\d+\t![^\n]+\n\n?\d+\t![^\n]+\n\n")
    alignsegments = re.split(splitpattern,conllinput)
    #Filter out empty align segments
    alignsegments = TrimList(alignsegments)

    #Test that same number of segments
    if len(alignsegments) != len(align_ids):
        raise AlignMismatch('The number of segments differs from the number in the source text: {}/{}'.format(len(alignsegments),len(align_ids)))

    #Get the current maximum indices:
    sentence_id = GetLastValue(con.FetchQuery("SELECT max(sentence_id) FROM {}".format(tl_dbtablename)))
    #Insert a new entry in the translation_ids table
    translator = input('Give the author for this translation:\n')
    con.query("INSERT INTO translation_ids (translator, sourcetext_id) VALUES(%s, %s)",(translator,text_id,),commit=True)
    translation_id  = GetLastValue(con.FetchQuery("SELECT max(id) FROM translation_ids WHERE sourcetext_id = %(sid)s",{'sid':text_id}))


    #Initialize variales for db insertion
    rowlist = list()
    bar = Bar('Preparing the data for insertion into the database', max=len(alignsegments))

    #================================================================================
    for idx, align_id in enumerate(align_ids):
        align_id = align_id[0]
        segment = alignsegments[idx]
        #Split each segment into lines (line=word with all the morphological and syntactic information)
        words = segment.splitlines()
        sentence_id += 1
        for word in words:
            #read all the information about the word
            if word == '':
                #empty lines are sentence breaks
                sentence_id += 1
            else:
                columns = word.split('\t')
                if len(columns) < 7:
                    #If an empty segment encountered
                    print('Note: an empty segment encountered at align_id {}'.format(align_id))
                    rowlist.append({'align_id'    : align_id,
                                    'sentence_id' : sentence_id,
                                    'text_id'     : text_id,
                                    'translation_id' : translation_id,
                                    'tokenid'     : 1,
                                    'token'       : 'EMPTYSEGMENT',
                                    'lemma'       : 'EMPTYSEGMENT',
                                    'pos'         : 'EMPTYSEGMENT',
                                    'feat'        : 'EMPTYSEGMENT',
                                    'head'        : 0,
                                    'deprel'      : 'EMPTY'})
                else:
                    #If this is a word with information, initialize a new row
                    if sl_dbtablename == 'fi_conll':
                        rowlist.append({'align_id'    : align_id,
                                        'sentence_id' : sentence_id,
                                        'text_id'     : text_id,
                                        'translation_id' : translation_id,
                                        'tokenid'     : columns[0],
                                        'token'       : columns[1],
                                        'lemma'       : columns[2],
                                        'pos'         : columns[4],
                                        'feat'        : columns[5],
                                        'head'        : columns[6],
                                        'deprel'      : columns[7]})

                    elif sl_dbtablename == 'ru_conll':
                        rowlist.append({'align_id'    : align_id,
                                        'sentence_id' : sentence_id,
                                        'text_id'     : text_id,
                                        'translation_id' : translation_id,
                                        'tokenid'     : columns[0],
                                        'token'       : columns[1],
                                        'lemma'       : columns[2],
                                        'pos'         : columns[4],
                                        'feat'        : columns[6],
                                        'head'        : columns[8],
                                        'deprel'      : columns[10]})
        bar.next()
    #================================================================================

    bar.finish()
    print('\nInserting to database, this might take a while...')
    con.BatchInsert(tl_dbtablename,rowlist)
    print('Done. Inserted {} rows.'.format(con.cur.rowcount))

if __name__ == "__main__":
    main()
