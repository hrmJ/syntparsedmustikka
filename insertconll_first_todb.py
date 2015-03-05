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
    #Connect to the database
    con = mydatabase('syntparfin','juho')
    try:
        conllinputfile = sys.argv[1]
        text_title = sys.argv[2]
    except:
        print('Usage: {} <path to finnish conll formatted text> <text title>'.format(sys.argv[0]))
        sys.exit(0)
    conllinputfile = sys.argv[1]
    text_title = sys.argv[2]
    #read the conll data as csv list
    with open(conllinputfile, 'r') as f:
        conllinput = list(csv.reader(f, delimiter='\t', quotechar = '\x07'))
    #create a new text id:
    tablename = 'text_ids'
    con.insertquery("INSERT INTO {} (title) values(%s)".format(tablename), (text_title,))
    text_id = con.nondictquery("SELECT max(id) FROM {}".format(tablename),("",))
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
            tablename = 'fi_conll'
            sql = "INSERT INTO {} (tokenid, form, lemma, pos, feat, head, deprel, sentence_id, align_id, text_id) VALUES  ( %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)".format(tablename)
            tokendata = (token[0], token[1], token[2], token[4], token[6], token[8], token[10], sentence_id, align_id, text_id)
            #insert the token
            con.insertquery(sql, tokendata)
            #Give some information on progress
            donepr = round(i / len(conllinput),1)
            sys.stdout.write("\r%d%%" % donepr)
            sys.stdout.flush()
#1}}}
#Start the script{{{1
if __name__ == "__main__":
    main()
#1}}}
