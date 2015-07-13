import logging
from search import Search, Match, Sentence, Word, ConstQuery, Db 
from collections import defaultdict

def LogNewDeprel(message):
    """Log the deprels name as header"""
    logging.info('{0}{1}{0}{2}{0}{1}{0}'.format('\n','='*50,message))

def log(message,counter=0, countmax=0):
    """Log just a simple message"""
    if countmax>0:
        print('{}  {}/{}'.format(message,counter,countmax), end = '\r')
    else:
        logging.info(message)


def simpleupdate(thisSearch,dbcon, deprel, dbtable):
    """In the prototypical case you just give the deprel of the contrastive layer"""
    logging.info('Updating {} items in the db'.format(len(thisSearch.listMatchids())))
    dbcon.query('UPDATE {table} SET contr_deprel = %(deprel)s WHERE id in %(idlist)s'.format(table=dbtable),{'deprel':deprel,'idlist':thisSearch.idlist})
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

def DependentToHead(dbcon,thisSearch,dbtable,matchdep,headdep):
    """Make the matched word the head and the 
    head the dependent"""

    log('Starting...')
    contr_heads = list()
    contr_deprels = list()
    error_sids = list()
    #########################################################################
    for key, matches in thisSearch.matches.items():
        for match in matches:
            try:
                mhead = match.matchedsentence.words[match.matchedword.head]
                #If the user wants the match's deprel to become what originally was the head's deprel:
                if matchdep == 'head':
                    newmatchdep = mhead.deprel
                else:
                    newmatchdep = matchdep
                contr_deprels.append({'baseval':match.matchedword.dbid,'changedval':newmatchdep})
                contr_deprels.append({'baseval':mhead.dbid,'changedval':headdep})
                contr_heads.append({'baseval':match.matchedword.dbid,'changedval':mhead.head})
                contr_heads.append({'baseval':mhead.dbid,'changedval':match.matchedword.tokenid})
            except KeyError:
                error_sids.append(matchedsentence.sentence_id)
    #########################################################################
    updates = [{'updatedcolumn':'contr_deprel','basecolumn':'id','valuelist':contr_deprels},
               {'updatedcolumn':'contr_head','basecolumn':'id','valuelist':contr_heads}]
    log('Updating the database, this might take long.. ')
    dbcon.BatchUpdate(table=dbtable, updates=updates)
    log('Update done. This will potentially effect {} database rows.'.format(dbcon.cur.rowcount))
    if error_sids:
        log('Key errors with sids {} (total {})'.format(','.join(error_sids),len(error_sids)))




class DepTypeUpdater:
    """General class for many kinds of updates"""

    ucolumn = 'contr_deprel'

    def __init__(self,dbcon,dbtable, message):
        """Initialize the connection oand other variables"""
        LogNewDeprel(message)
        self.dbcon = dbcon
        self.dbtable = dbtable

    def rename(self, oldname, newname, oldaslist=False):
        """Rename a category"""
        if oldaslist:
            log('Renaming {} to {}.'.format(', '.join(oldname),newname))
            self.dbcon.query('UPDATE {} SET contr_deprel = %(contrdep)s WHERE deprel in %(deprel)s'.format(self.dbtable),{'contrdep':newname,'deprel':oldname})
        else:
            log('Renaming {} to {}.'.format(oldname,newname))
            self.dbcon.query('UPDATE {} SET contr_deprel = %(contrdep)s WHERE deprel = %(deprel)s'.format(self.dbtable),{'contrdep':newname,'deprel':oldname})
        log('Update done. Renamed {} database rows.'.format(self.dbcon.cur.rowcount))

    def UseOriginals(self, olddeprels):
        """Update directly with sql queries"""
        log('Using the original names for {} '.format(', '.join(olddeprels)))
        self.dbcon.query('UPDATE fi_conll SET contr_deprel = deprel WHERE deprel in %(deprel)s',{'deprel':olddeprels})
        log('Update done. Effected {} database rows.'.format(self.dbcon.cur.rowcount))

    def InitializeUpdate(self, message):
        """Some standardized starting procedures for updates"""

        log(message)
        self.contr_heads = list()
        self.contr_deprels = list()
        self.error_sids = list()
        self.updates = list()

    def FinalizeUpdate(self):
        """ Do the actual updating for functions such as DependentSameAsHead and DependentToHead """

        if self.error_sids:
            log('Key errors with sids {} (total {})'.format(','.join(error_sids),len(error_sids)))
        #Add all the columns to be changed:
        if self.contr_deprels:
            self.updates.append({'updatedcolumn':'contr_deprel','basecolumn':'id','valuelist':self.contr_deprels})
        if self.contr_heads:
            self.updates.append({'updatedcolumn':'contr_head','basecolumn':'id','valuelist':self.contr_heads})

        #Update:
        log('Updating the database, this might take long.. ')
        self.dbcon.BatchUpdate(table=self.dbtable, updates=self.updates)
        log('Update done. This will potentially effect {} database rows.'.format(self.dbcon.cur.rowcount))

    def simpleupdate(self, deprel):
        """In the prototypical case you just give the deprel of the contrastive layer"""
        logging.info('Updating {} items in the db'.format(len(self.search.listMatchids())))
        if self.search.idlist:
            self.dbcon.query('UPDATE {table} SET contr_deprel = %(deprel)s WHERE id in %(idlist)s'.format(table=self.dbtable),{'deprel':deprel,'idlist':self.search.idlist})
            log('to be updated: {} database rows.'.format(self.dbcon.cur.rowcount))
        else:
            log('0 updates')

    def updateByQuery(self, contr_deprel, where, valuedict, message='update by query'):
        log(message)
        valuedict['contrdep'] = contr_deprel
        self.dbcon.query('UPDATE {} SET {} = %(contrdep)s WHERE {}'.format(self.dbtable,DepTypeUpdater.ucolumn, where),valuedict)
        log('to be updated: {} database rows.'.format(self.dbcon.cur.rowcount))
    
    def Update(self, updateType, matchdep='', headdep='', message='Starting...'):
        """Make the matched word the head and the head the dependent"""
        self.InitializeUpdate(message)
        #########################################################################
        for key, matches in self.search.matches.items():
            for match in matches:
                if not match.CatchHead():
                    self.error_sids.append(matchedsentence.sentence_id)
                elif updateType == 'DependentOfSameAsHead':
                    self.contr_deprels.append({'baseval':match.matchedword.dbid,'changedval':matchdep})
                    self.contr_heads.append({'baseval':match.matchedword.dbid,'changedval':match.headword.head})
                elif updateType == 'DependentBecomesHead':
                    #New values for the match
                    self.contr_deprels.append({'baseval':match.matchedword.dbid,'changedval':match.headword.deprel})
                    self.contr_heads.append({'baseval':match.matchedword.dbid,'changedval':match.headword.head})
                    #New values for the head
                    self.contr_deprels.append({'baseval':match.headword.dbid,'changedval':headdep})
                    self.contr_heads.append({'baseval':match.headword.dbid,'changedval':match.matchedword.tokenid})
                    #Set the match head for ALL the words that were originally dependent of the head:
                    #TÄMÄ ON KUITENKIN ONGELMALLISTA! vrt. parfin sentence_id 36505 >>>
                    #match.matchedsentence.listDependents(match.headword.tokenid)
                    #for dep in match.matchedsentence.dependentlist:
                    #    self.contr_heads.append({'baseval':dep.dbid,'changedval':match.matchedword.tokenid})
        #########################################################################
        self.FinalizeUpdate()

