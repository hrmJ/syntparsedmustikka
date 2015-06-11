import logging
from search import Search, Match, Sentence, Word, ConstQuery, Db 

def LogNewDeprel(message):
    """Log the deprels name as header"""
    logging.info('{0}{1}{0}{2}{0}{1}{0}'.format('\n','='*50,message))

def log(message):
    """Log just a simple message"""
    logging.info(message)

def simpleupdate(thisSearch,dbcon, deprel):
    """In the prototypical case you just give the deprel of the contrastive layer"""
    logging.info('Updating {} items in the db'.format(len(thisSearch.listMatchids())))
    dbcon.query('UPDATE ru_conll SET contr_deprel = %(deprel)s WHERE id in %(idlist)s',{'deprel':deprel,'idlist':thisSearch.idlist})
    logging.info('to be updated: {} database rows.'.format(dbcon.cur.rowcount))

def makeSearch(ConditionColumns,database,dbtable,headcond=None,depcond=None,appendconditioncolumns=True):
    Db.searched_table = dbtable
    thisSearch = Search(database,askname=False)
    logging.info('Starting the search..')
    thisSearch = Search(database,askname=False)
    if appendconditioncolumns:
        thisSearch.ConditionColumns.append(ConditionColumns)
    else:
        thisSearch.ConditionColumns = ConditionColumns
    thisSearch.headcond = headcond
    thisSearch.depcond = depcond
    thisSearch.BuildSubQuery()
    thisSearch.find()
    logging.info('Search committed')
    return thisSearch

def DependentSameAsHead(dbcon,thisSearch,dbtable,matchdep):
    """Make the matched word'shead same as the head's head"""
    updated=0
    for key, matchlist in thisSearch.matches.items():
        for match in matchlist:
            try:
                mhead = match.matchedsentence.words[match.matchedword.head]
                dbcon.query('UPDATE {table} SET contr_head = %(contrhead)s, contr_deprel = %(contrdep)s WHERE id = %(matchid)s'.format(table=dbtable),{'contrhead':mhead.head,'contrdep':matchdep,'matchid':match.matchedword.dbid})
                updated += 1
            except KeyError:
                log('KeyError  with word {}, sentence {}'.format(match.matchedword.token,match.matchedsentence.sentence_id))
    log('{}: updated {} items in the db'.format(matchdep,updated))



def DependentToHead(dbcon,thisSearch,dbtable,matchdep, headdep):
    """Make the matched word the head and the 
    head the dependent"""

    sql = "UPDATE {table} SET contr_deprel = CASE id".format(table=dbtable)
    sqlvals = list()
    idvals = list()
    log('Starting...')
    #First, set deprel
    for key, matches in thisSearch.matches.items():
        for match in matches:
            try:
                mhead = match.matchedsentence.words[match.matchedword.head]
                #If the user wants the match's deprel to become what originally was the head's deprel:
                if matchdep == 'head':
                    newmatchdep = mhead.deprel
                else:
                    newmatchdep = matchdep
                #head
                sql += """ WHEN %s THEN %s"""
                sqlvals.append(mhead.dbid)
                sqlvals.append(headdep)
                idvals.append(mhead.dbid)
                #match
                sql += """ WHEN %s THEN %s"""
                sqlvals.append(match.matchedword.dbid)
                sqlvals.append(newmatchdep)
                idvals.append(match.matchedword.dbid)
            except KeyError:
                log('KeyError  with word {}, sentence {}'.format(match.matchedword.token,match.matchedsentence.sentence_id))
    #Then set heads
    sql += " END, contr_head = CASE id"
    for key, matches in thisSearch.matches.items():
        for match in matches:
            nonconj = match.matchedword
            try:
                mhead = match.matchedsentence.words[match.matchedword.head]
                #head
                sql += """ WHEN %s THEN %s"""
                sqlvals.append(mhead.dbid)
                sqlvals.append(match.matchedword.tokenid)
                #nonconj
                sql += """ WHEN %s THEN %s"""
                sqlvals.append(match.matchedword.dbid)
                sqlvals.append(mhead.head)
            except KeyError:
                logging.info('Key error with sentence id {}'.format(match.matchedsentence.sentence_id))
    sql += " END WHERE id in %s"
    sqlvals.append(tuple(idvals))
    log('Execute the query...')
    dbcon.query(sql,tuple(sqlvals))
    logging.info("UPDATED {} rows ".format(dbcon.cur.rowcount))

