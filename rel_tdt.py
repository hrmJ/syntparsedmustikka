from deptypetools import  makeSearch, log
import pickle
import logging
import sys
import csv
import string
from dbmodule import psycopg, mydatabase

def fakenonrel(word):
    """Keksitään relatiivipronominille ei-relatiivinen korvaaja:"""
    if word == 'joka':    
        return 'se'
    elif word =='jotka':
        return 'ne'
    elif word =='jossa':
        return 'siinä'
    elif word =='mitä':
        return 'sitä'
    elif word =='jonka':
        return 'sen'
    elif word =='jota':
        return 'sitä'
    elif word =='mikä':
        return 'se'
    elif word =='josta':
        return 'siitä'
    elif word =='joita':
        return 'niitä'
    elif word =='johon':
        return 'siihen'
    elif word =='jolla':
        return 'sillä'
    elif word =='missä':
        return 'siinä'
    elif word =='minkä':
        return 'sen'
    elif word =='jolloin':
        return 'silloin'
    elif word =='joissa':
        return 'niissä'
    elif word =='joilla':
        return 'niillä'
    elif word =='joista':
        return 'niistä'
    elif word =='joiden':
        return 'niiden'
    elif word =='mistä':
        return 'siitä'
    elif word =='joihin':
        return 'niihin'
    elif word =='mihin':
        return 'siihen'
    elif word =='jolle':
        return 'sille'
    elif word =='jonne':
        return 'sinne'
    elif word =='Mitä':
        return 'Sitä'
    elif word =='joille':
        return 'niille'
    elif word =='millä':
        return 'sillä'
    elif word =='jolta':
        return 'siltä'
    elif word =='joilta':
        return 'niiltä'
    elif word =='mille':
        return 'sille'
    elif word =='mitkä':
        return 'ne'
    elif word =='joina':
        return 'niinä'
    elif word =='minne':
        return 'sinne'
    elif word =='mitähän':
        return 'sitähän'
    elif word =='jona':
        return 'sinä'
    else:
        return word

def getRelDict(thisSearch):
    """Fetch the relative clauses to a dict"""
    #Get the actual relative clauses and save information about them in a list of dicts
    log('Processing all the relative clauses to a list')
    relclauses = list()
    for key, matches in thisSearch.matches.items():
        for match in matches:
            delthese = list()
            for tokenid, word in match.matchedsentence.words.items():
                #Assume the relative word is the first word of the clause and remove all the preceding words
                if word.tokenid < match.matchedword.tokenid:
                    delthese.append(word.tokenid)
            for delthis in delthese:
                del(match.matchedsentence.words[delthis])
            match.matchedword.token = fakenonrel(match.matchedword.token)
            match.BuildSentencePrintString()
            relclauses.append({'clause':'','dbid':0})
            relclauses[-1]["clause"] = match.matchedsentence.cleanprintstring
            relclauses[-1]["dbid"] = match.matchedword.dbid
    #save as pickle
    pickle.dump(relclauses, open('relclauses.p', "wb"))
    return relclauses

def PrintRelClausesToFile(relclauses):
    clausestring = ''
    for relclause in relclauses:
        clausestring += '\n#\n' + relclause['clause']
    f = open('parserinput.txt','w')
    f.write(clausestring)
    f.close()

def ReadConllInput(conllinputfile):
    """Read the input from the reparsed relativizers"""
    newdeprels = list()

    with open(conllinputfile, 'r') as f:
        conllinput = list(csv.reader(f, delimiter='\t', quotechar = '\x07'))
    #Loop through the lines
    for token in conllinput:
        if not token:
            #If a blank line was encountered:
            pass
        elif token[1] == '#':
            #if a border mark encountered
            newdeprels.append('')
        else:
            #if an ordinary token was encountered:
            if not newdeprels[-1]:
                #DEPREL is column no 10
                deprelcol = 10
                newdeprels[-1] = token[deprelcol]

    return newdeprels

def UpdateContrRel(dbcon,originalClauses,newdeprels):
    """Update the new deprels to 
    the database according to the reparsed file"""

    contr_deprels = list()
    #Pair the relativizers' dbids and the reparsed deprels:
    for idx, clause in enumerate(originalClauses):
        contr_deprels.append({'baseval':clause['dbid'],'changedval':newdeprels[idx]})
    updates = [{'updatedcolumn':'contr_deprel','basecolumn':'id','valuelist':contr_deprels}]

    #Insert to database:
    log('Updating the database, this might take long.. ')
    dbcon.BatchUpdate(table='fi_conll', updates=updates)
    log('Update done. This will potentially effect {} database rows.'.format(dbcon.cur.rowcount))





