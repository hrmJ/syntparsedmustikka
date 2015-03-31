#! /usr/bin/env python
#Import modules{{{1
#For unicode support:
import codecs
#other
import csv
import sys
#xml parsing
from lxml import etree
#local modules
from dbmodule import mydatabase
#1}}}
#Main module{{{1
def main():
    # Test if enough arguments   
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
    #read the conll data as csv list
    with open(conllinputfile, 'r') as f:
        conllinput = list(csv.reader(f, delimiter='\t', quotechar = '\x07'))
    #Connect to the database
    con = mydatabase(dbname,'juho')
    #create a new text id:
    #fetch the id of the pair that is already inserted
    text_id = con.nondictquery("SELECT id FROM {} WHERE id = %s".format('text_ids'),(text_id,))
    try:
        text_id = text_id[0]
    except:
        print('No such id!')
        sys.exit(0)
    #Get all the align ids that were inserted with the first file
    align_ids = con.nondictquery("SELECT DISTINCT align_id FROM {} WHERE text_id = %s order by align_id".format(sl_dbtablename),(text_id,))
    #initialize a counter to track the align ids
    align_id_counter=0;
    #initialize a progress counter to be shown to the user
    i=0
    #Loop through the lines
    for token in conllinput:
    #increment the counter
        i += 1
        #If a blank line was encountered:
        if not token:
            #create a new sentence id:
            if "ru_" in tl_dbtablename:
                tablename = 'sentence_ids_ru'
            elif "fi_" in tl_dbtablename:
                tablename = 'sentence_ids_fi'
            con.insertquery("INSERT INTO {} values(default)".format(tablename), ("",))
            sentence_id = con.nondictquery("SELECT max(id) FROM {}".format(tablename),("",))
            sentence_id = sentence_id[0]
        #If a new alignment unit was encountered:
        elif token[1] == '#':
            #Use the next align id of the already inserted text
            align_id = align_ids[align_id_counter]
            #increment the counter
            align_id_counter += 1
        #if an ordinary token was encountered:
        else:
            tablename = tl_dbtablename
            #The finnish and russian parser output are formatted a little differently:
            if tl_dbtablename == 'ru_conll':
                sql = "INSERT INTO {} (tokenid, form, lemma, pos, feat, head, deprel, sentence_id, align_id, text_id) VALUES  ( %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)".format(tablename)
                tokendata = (token[0], token[1], token[2], token[4], token[5], token[6], token[7], sentence_id, align_id, text_id)
            elif tl_dbtablename == 'fi_conll':
                sql = "INSERT INTO {} (tokenid, form, lemma, pos, feat, head, deprel, sentence_id, align_id, text_id) VALUES  ( %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)".format(tablename)
                tokendata = (token[0], token[1], token[2], token[4], token[6], token[8], token[10], sentence_id, align_id, text_id)
            #insert the token
            con.insertquery(sql, tokendata)
            #Give some information on progress
            print('{}/{}'.format(i,len(conllinput)), end='\r')
#1}}}
#Start the script{{{1
if __name__ == "__main__":
    main()
#1}}}
