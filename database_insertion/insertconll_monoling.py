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
    try:
        conllinputfile = sys.argv[1]
        text_title = sys.argv[2]
        sl_dbname = sys.argv[3]
        sl_dbtablename = sys.argv[4]
    except:
        print('Usage: {} <path to conll formatted text file> <text title> <database name> <source language database table name>'.format(sys.argv[0]))
        sys.exit(0)
    conllinputfile = sys.argv[1]
    text_title = sys.argv[2]
    #read the conll data as csv list
    with open(conllinputfile, 'r') as f:
        conllinput = list(csv.reader(f, delimiter='\t', quotechar = '\x07'))
    #create a new text id:
    tablename = 'text_ids'
    #Connect to the database
    con = mydatabase(sl_dbname,'juho')
    #Insert text metadata
    con.insertquery("INSERT INTO {} (title) values(%s)".format(tablename), (text_title,))
    text_id = con.nondictquery("SELECT max(id) FROM {}".format(tablename),("",))
    text_id = text_id[0]
    #initialize a counter to be shown to the user
    i=0
    #Loop through the lines
    for token in conllinput:
    #increment the counter
        i += 1
        #If a blank line was encountered:
        if not token:
            #create a new sentence id:
            tablename = 'sentence_ids'
            con.insertquery("INSERT INTO {} values(default)".format(tablename), ("",))
            sentence_id = con.nondictquery("SELECT max(id) FROM {}".format(tablename),("",))
            sentence_id = sentence_id[0]
        #If a new alignment unit was encountered:
        elif token[1] == '#':
            tablename = 'align_ids'
            #create a new alignment id:
            con.insertquery("INSERT INTO {} values(default)".format(tablename), ("",))
            align_id = con.nondictquery("SELECT max(id) FROM {}".format(tablename),("",))
            align_id = align_id[0]
        #if an ordinary token was encountered:
        else:
            tablename = sl_dbtablename
            if sl_dbtablename == 'ru_conll':
                sql = "INSERT INTO {} (tokenid, token, lemma, pos, feat, head, deprel, sentence_id, align_id, text_id) VALUES  ( %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)".format(tablename)
                tokendata = (token[0], token[1], token[2], token[4], token[5], token[6], token[7], sentence_id, align_id, text_id)
            elif sl_dbtablename == 'fi_conll':
                sql = "INSERT INTO {} (tokenid, token, lemma, pos, feat, head, deprel, sentence_id, align_id, text_id) VALUES  ( %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)".format(tablename)
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
