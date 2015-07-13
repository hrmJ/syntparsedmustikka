#! /usr/bin/env python
#psql integration:{{{2
import psycopg2
import psycopg2.extras
from psycopg2.extensions import AsIs
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

class psycopg:

    def __init__(self,dbname,username,autocom=False):
       self.connection = psycopg2.connect("dbname='{}' user='{}'".format(dbname, username))
       self.connection.autocommit = autocom
       self.cur = self.connection.cursor()
       self.dbname = dbname

    def query(self, SQL, valuetuple=("empty",)):
        """A general query for inserting updating etc."""
        try:
            self.cur.execute(SQL, valuetuple)
        except psycopg2.Error as e:
            print("Somerthing wrong with the query")
            print ("Psql gives the error: {}".format(e.pgerror))

    def FetchQuery(self, SQL,valuetuple=("empty",)):
        " Query with a non-dictionary cursor "
        try:
            self.cur.execute(SQL, valuetuple)
            return self.cur.fetchall()
        except psycopg2.Error as e:
            print("Something wrong with the query")
            print(SQL)
            print ("Psql gives the error: {}".format(e.pgerror))

    def BatchUpdate(self,table,updates):
        """Do updates for large amounts of data
        ===================================================

        + updates: a list of dicts. The dicts must have  three keys, 'valuelist', 'updatedcolumn' and 'basecolumn'.
            + valuelist: also a list of dicts. Each list item must have the keys 'baseval' and 'changedval'
                -  baseval     : the value of the column in the WHERE clause (typically id)
                -  changedval  : the new value of the *updatedcolumn*
            - updatedcolumn: the column the values of which are being changed, 
            - basecolumn: the column that specifies what the updated
              value will be: in other words, what typically would reside
              in the WHERE clause (update footable set foo=bar WHERE BASECOLUMN = foobar)

        """

        queryvalues = dict()
        sql = "UPDATE {table} SET ".format(table=table)

        qrange = 'WHERE '
        rangevaluelist=list()
        for uidx, update in enumerate(updates):
            sql += " {column} = CASE {basecolumn} ".format(table=table,column=update['updatedcolumn'],basecolumn=update['basecolumn'])
            rangevaluelist.append(list())
            for idx, valuepair in enumerate(update['valuelist']):
                basecolref = '{}{}{}'.format(uidx,'basecol',idx) 
                changedcolref = '{}{}{}'.format(uidx,'changedcol',idx) 
                queryvalues[basecolref]=valuepair['baseval']
                queryvalues[changedcolref]=valuepair['changedval']
                sql += 'WHEN %({basecolref})s THEN %({changedcolref})s '.format(basecolref=basecolref, changedcolref=changedcolref)
                rangevaluelist[-1].append(valuepair['baseval'])
            sql += " END"
            qrange += ' {basecol} IN %({rangevals})s'.format(basecol=update['basecolumn'],rangevals='rangevals{}'.format(uidx))
            queryvalues['rangevals{}'.format(uidx)] = tuple(rangevaluelist[-1])
            if uidx +1 < len(updates):
                sql += ", "
                qrange += " OR "

        sql += " " + qrange

        self.cur.execute(sql, queryvalues)


class mydatabase:
    """Establish a connection to database and create two cursors for use"""

    def __init__(self,dbname,username):
       self.connection = psycopg2.connect("dbname='{}' user='{}'".format(dbname, username))
       self.connection.autocommit = True
       self.dictcur = self.connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
       self.cur = self.connection.cursor()
       self.dbname = dbname

    def insertquery(self, SQL, valuetuple=("empty",)):
        """A general query for inserting updating etc."""
        try:
            self.cur.execute(SQL, valuetuple)
        except psycopg2.Error as e:
            print("Somerthing wrong with the query")
            print ("Psql gives the error: {}".format(e.pgerror))

    def dictquery(self, SQL,valuetuple=("empty",)):
        """Query with a dictionary cursor"""
        try:
            self.dictcur.execute(SQL, valuetuple)
            return self.dictcur.fetchall()
        except psycopg2.Error as e:
            print("Somerthing wrong with the query")
            print ("Psql gives the error: {}".format(e.pgerror))

    def nondictquery(self, SQL,valuetuple=("empty",)):
        " Query with a non-dictionary cursor "
        try:
            self.cur.execute(SQL, valuetuple)
            return self.cur.fetchall()
        except psycopg2.Error as e:
            print("Somerthing wrong with the query")
            print(SQL)
            print ("Psql gives the error: {}".format(e.pgerror))

    def OneResultQuery(self, SQL,valuetuple=("empty",)):
        """Query with a non-dictionary cursor that returns only one
        value """
        try:
            self.cur.execute(SQL, valuetuple)
            result = self.cur.fetchall()
            return result[0]
        except psycopg2.Error as e:
            print("Somerthing wrong with the query")
            print(SQL)
            print ("Psql gives the error: {}".format(e.pgerror))


def CreateSQLAsession(dbname):
    """Create a temporal session object"""
    engine = create_engine('postgresql:///{}'.format(dbname), echo=False)
    # create a Session
    Session = sessionmaker(bind=engine)
    return Session()

class SqlaCon:
    """Autoconn:ct to psql via sqlalchemy"""

    def __init__(self,Base,engine):
        self.Base = Base
        self.engine = engine

    def LoadSession(self):
        """"""
        metadata = self.Base.metadata
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
    def insert(self, dbobj):
        """Insert via sqla"""
        self.LoadSession()
        self.session.add(dbobj)
        self.session.commit()
